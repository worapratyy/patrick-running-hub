#!/usr/bin/env python3
"""
Strava → runs.json sync script.
Fetches all Run/VirtualRun activities from Strava and writes data/runs.json
in the same format as the legacy Railway /api/runs/1 endpoint.

Prints NEW_REFRESH_TOKEN=<token> so GitHub Actions can rotate the secret.

Env vars required:
  STRAVA_CLIENT_ID
  STRAVA_CLIENT_SECRET
  STRAVA_REFRESH_TOKEN

Output: data/runs.json (relative to repo root, or RUNS_JSON_PATH env override)
"""
import json
import os
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

CLIENT_ID     = os.environ["STRAVA_CLIENT_ID"]
CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]
OUTPUT_PATH   = Path(os.environ.get("RUNS_JSON_PATH", "data/runs.json"))


def refresh_access_token():
    data = urllib.parse.urlencode({
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type":    "refresh_token",
        "refresh_token": REFRESH_TOKEN,
    }).encode()
    req = urllib.request.Request("https://www.strava.com/oauth/token", data=data)
    with urllib.request.urlopen(req) as resp:
        tokens = json.loads(resp.read())
    return tokens["access_token"], tokens["refresh_token"]


def fetch_all_activities(access_token):
    all_acts = []
    page = 1
    while True:
        url = f"https://www.strava.com/api/v3/athlete/activities?per_page=100&page={page}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
        with urllib.request.urlopen(req) as resp:
            batch = json.loads(resp.read())
        if not batch:
            break
        all_acts.extend(batch)
        page += 1
    return all_acts


def fetch_activity_detail(access_token, activity_id):
    """Fetch one detailed activity so per-kilometre splits are available."""
    url = f"https://www.strava.com/api/v3/activities/{activity_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_activity_streams(access_token, activity_id):
    """Fetch distance and cadence streams for per-kilometre cadence."""
    url = f"https://www.strava.com/api/v3/activities/{activity_id}/streams?keys=distance,cadence&key_by_type=true"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def stream_values(streams, key):
    stream = streams.get(key) if isinstance(streams, dict) else None
    if isinstance(stream, dict):
        return stream.get("data", [])
    return stream or []


def cadence_by_split(splits, streams):
    distances = stream_values(streams, "distance")
    cadences = stream_values(streams, "cadence")
    if not distances or not cadences or len(distances) != len(cadences):
        return {}
    result = {}
    start_m = 0
    for index, split in enumerate(splits):
        end_m = start_m + (split.get("distance") or 0)
        values = [
            cadence
            for distance, cadence in zip(distances, cadences)
            if (distance <= end_m if index == 0 else start_m < distance <= end_m)
            and cadence is not None
        ]
        if values:
            result[split.get("split")] = round(mean(values) * 2, 1)
        start_m = end_m
    return result


def split_to_record(split, lap=None, stream_cadence=None):
    distance_km = (split.get("distance") or 0) / 1000
    moving_time = split.get("moving_time") or 0
    pace_sec = moving_time / distance_km if distance_km else 0
    cadence = split.get("average_cadence")
    if cadence is None and lap:
        cadence = lap.get("average_cadence")
    if cadence is None and stream_cadence is not None:
        cadence = stream_cadence / 2
    heart_rate = split.get("average_heartrate")
    elevation = split.get("elevation_difference")
    return {
        "km": split.get("split"),
        "dist": round(distance_km, 2),
        "pM": int(pace_sec // 60),
        "pS": int(pace_sec % 60),
        "hr": round(heart_rate, 1) if heart_rate else None,
        "cad": round(cadence * 2, 1) if cadence else None,
        "elev": round(elevation, 1) if elevation is not None else None,
    }


def activity_to_run(act, detail=None, streams=None, previous=None):
    dist_km   = (act.get("distance") or 0) / 1000
    move_time = act.get("moving_time") or 0
    pace_sec  = (move_time / dist_km) if dist_km > 0 else 0
    hr        = act.get("average_heartrate")
    cad       = act.get("average_cadence")
    is_indoor = act.get("trainer", False) or act.get("sport_type") == "VirtualRun"
    start_local = act.get("start_date_local", "")

    run = {
        "id":          act.get("id"),
        "date":       start_local[:10] if start_local else None,
        "dist":       round(dist_km, 2),
        "pM":         int(pace_sec // 60),
        "pS":         int(pace_sec % 60),
        "hr":         round(hr, 1) if hr else None,
        "cad":        round(cad * 2, 1) if cad else None,  # strides/min → steps/min
        "name":       act.get("name"),
        "indoor":     bool(is_indoor),
        "sport_type": act.get("sport_type"),
    }
    if detail and detail.get("splits_metric"):
        laps = detail.get("laps", [])
        stream_cadence = cadence_by_split(detail["splits_metric"], streams or {})
        run["splits"] = [
            split_to_record(
                s,
                laps[index] if index < len(laps) else None,
                stream_cadence.get(s.get("split")),
            )
            for index, s in enumerate(detail["splits_metric"])
        ]
    elif previous and previous.get("splits"):
        run["splits"] = previous["splits"]
    return run


def main():
    print("🔄 Refreshing Strava token...")
    access_token, new_refresh_token = refresh_access_token()
    print(f"✅ Access token obtained. New refresh token: ...{new_refresh_token[-6:]}")

    print("📥 Fetching all activities...")
    activities = fetch_all_activities(access_token)
    print(f"   Total fetched: {len(activities)}")

    activities = [a for a in activities if a.get("sport_type") in ("Run", "VirtualRun")]
    previous_runs = {}
    if OUTPUT_PATH.exists():
        try:
            previous_runs = {
                str(r["id"]): r
                for r in json.loads(OUTPUT_PATH.read_text()).get("runs", [])
                if r.get("id") is not None
            }
        except (OSError, json.JSONDecodeError):
            print("⚠️ Could not read previous runs.json; continuing without split cache.")

    # The list endpoint has summary activities only. Detail calls are limited so
    # the sync stays below Strava's API rate limit while enriching new runs.
    detail_limit = int(os.environ.get("STRAVA_DETAIL_LIMIT", "8"))
    newest_first = sorted(activities, key=lambda a: a.get("start_date_local", ""), reverse=True)
    new_ids = [str(a["id"]) for a in newest_first if a.get("id") is not None and str(a["id"]) not in previous_runs]
    missing_split_ids = [
        str(a["id"])
        for a in newest_first
        if a.get("id") is not None
        and (
            not previous_runs.get(str(a["id"]), {}).get("splits")
            or any(s.get("cad") is None for s in previous_runs[str(a["id"])]["splits"])
        )
    ]
    detail_ids = list(dict.fromkeys(new_ids + missing_split_ids))[:detail_limit]
    details = {}
    streams = {}
    for activity_id in detail_ids:
        try:
            details[activity_id] = fetch_activity_detail(access_token, activity_id)
            streams[activity_id] = fetch_activity_streams(access_token, activity_id)

        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            print(f"⚠️ Split detail unavailable for activity {activity_id}: {exc}")

    runs = [
        activity_to_run(
            a,
            details.get(str(a.get("id"))),
            streams.get(str(a.get("id"))),
            previous_runs.get(str(a.get("id"))),
        )
        for a in activities
    ]
    runs.sort(key=lambda r: r["date"] or "")
    print(f"   Run activities: {len(runs)}")

    payload = {
        "last_synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "runs": runs,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"✅ Written to {OUTPUT_PATH}")

    # GitHub Actions reads this line to rotate the secret
    print(f"NEW_REFRESH_TOKEN={new_refresh_token}")


if __name__ == "__main__":
    main()
