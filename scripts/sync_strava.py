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
from pathlib import Path

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


def activity_to_run(act):
    dist_km   = (act.get("distance") or 0) / 1000
    move_time = act.get("moving_time") or 0
    pace_sec  = (move_time / dist_km) if dist_km > 0 else 0
    hr        = act.get("average_heartrate")
    cad       = act.get("average_cadence")
    is_indoor = act.get("trainer", False) or act.get("sport_type") == "VirtualRun"
    start_local = act.get("start_date_local", "")

    return {
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


def main():
    print("🔄 Refreshing Strava token...")
    access_token, new_refresh_token = refresh_access_token()
    print(f"✅ Access token obtained. New refresh token: ...{new_refresh_token[-6:]}")

    print("📥 Fetching all activities...")
    activities = fetch_all_activities(access_token)
    print(f"   Total fetched: {len(activities)}")

    runs = [
        activity_to_run(a)
        for a in activities
        if a.get("sport_type") in ("Run", "VirtualRun")
    ]
    runs.sort(key=lambda r: r["date"] or "")
    print(f"   Run activities: {len(runs)}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps({"runs": runs}, indent=2))
    print(f"✅ Written to {OUTPUT_PATH}")

    # GitHub Actions reads this line to rotate the secret
    print(f"NEW_REFRESH_TOKEN={new_refresh_token}")


if __name__ == "__main__":
    main()
