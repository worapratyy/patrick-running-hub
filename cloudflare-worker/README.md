# Strava → GitHub Webhook Bridge (Cloudflare Worker)

Every time Patrick finishes a run, Strava fires this Worker, which triggers
the `sync-strava.yml` GitHub Actions workflow to refresh `data/runs.json`.

---

## Step 1 — Sign up for Cloudflare (free)

1. Go to <https://dash.cloudflare.com/sign-up>
2. Create a free account — no credit card required.

---

## Step 2 — Create the Worker

1. In the Cloudflare dashboard, click **Workers & Pages** in the left sidebar.
2. Click **Create application → Create Worker**.
3. Give it a name, e.g. `patrick-strava-webhook`, then click **Deploy**.
4. Click **Edit code** (or **Quick edit**).
5. Delete the placeholder code and paste the entire contents of `index.js`.
6. Click **Save and deploy**.

Copy the Worker URL shown at the top — it looks like:

```text
https://patrick-strava-webhook.<your-subdomain>.workers.dev
```

If you enable `WEBHOOK_PATH_SECRET`, the callback URL becomes:

```text
https://patrick-strava-webhook.<your-subdomain>.workers.dev/<WEBHOOK_PATH_SECRET>
```

---

## Step 3 — Set environment variables

From the Worker's overview page, go to **Settings → Variables** and add:

| Variable name | Value |
|---|---|
| `STRAVA_VERIFY_TOKEN` | Random shared verification token for Strava webhook setup |
| `GH_PAT` | GitHub PAT with `repo` + `workflow` scopes |
| `WEBHOOK_PATH_SECRET` | Optional random path segment to reduce drive-by POST spam |
| `STRAVA_ATHLETE_ID` | Optional Strava athlete id; events from other owners are ignored |

To get the GitHub PAT for the currently logged-in GitHub account:

```bash
gh auth token
```

> Do not commit real Strava client secrets, GitHub tokens, refresh tokens, or
> webhook tokens to this repository. Keep real values in GitHub Secrets and
> Cloudflare Worker variables only.

---

## Step 4 — Register the Strava webhook

Use your Strava app's real client id/secret locally. Replace all placeholders
before running this command:

```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -F client_id="$STRAVA_CLIENT_ID" \
  -F client_secret="$STRAVA_CLIENT_SECRET" \
  -F callback_url="https://YOUR-WORKER.workers.dev/YOUR_WEBHOOK_PATH_SECRET" \
  -F verify_token="$STRAVA_VERIFY_TOKEN"
```

If you do not set `WEBHOOK_PATH_SECRET`, use the root Worker URL as the
`callback_url` instead.

A successful response looks like:

```json
{"id": 12345, "callback_url": "https://YOUR-WORKER.workers.dev/..."}
```

---

## Step 5 — Verify the subscription

```bash
curl -G https://www.strava.com/api/v3/push_subscriptions \
  -d client_id="$STRAVA_CLIENT_ID" \
  -d client_secret="$STRAVA_CLIENT_SECRET"
```

You should see your webhook listed with its `id` and `callback_url`.

---

## How it works

```text
Patrick finishes run
       ↓
   Strava fires POST to Worker
       ↓
   Worker checks path secret / owner id / event type
       ↓
   Worker calls GitHub repository_dispatch → event_type: strava-activity
       ↓
   .github/workflows/sync-strava.yml triggers
       ↓
   sync_strava.py runs → data/runs.json updated → dashboard refreshes
```

---

## Troubleshooting

- **404 on verification**: `WEBHOOK_PATH_SECRET` is set but the callback URL path does not match it.
- **403 on verification**: `STRAVA_VERIFY_TOKEN` does not match the Worker variable.
- **502 on activity**: Check `GH_PAT` has `repo` and `workflow` scopes; run `gh auth token` to get a fresh one.
- **No workflow after POST**: If `STRAVA_ATHLETE_ID` is set, confirm it matches the event `owner_id`.
- **Logs**: In the Cloudflare dashboard, go to Workers → your worker → **Logs** tab for real-time logs.
