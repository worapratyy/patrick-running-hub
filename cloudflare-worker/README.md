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

```
https://patrick-strava-webhook.<your-subdomain>.workers.dev
```

---

## Step 3 — Set environment variables

1. From the Worker's overview page, go to **Settings → Variables**.
2. Under **Environment Variables**, click **Add variable** twice:

| Variable name        | Value                          |
|----------------------|--------------------------------|
| `STRAVA_VERIFY_TOKEN`| `patrick-strava-2026`          |
| `GH_PAT`             | *(paste your GitHub PAT)*      |

   To get the GitHub PAT, run in terminal: `gh auth token`

3. Click **Save and deploy** after adding both variables.

---

## Step 4 — Register the Strava webhook

Run this curl command, replacing `YOUR-WORKER` with your actual Worker subdomain:

```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -F client_id=206570 \
  -F client_secret=98afb2de9c8f69e2b3c05b0f1bff1010e33e2e97 \
  -F callback_url=https://YOUR-WORKER.workers.dev \
  -F verify_token=patrick-strava-2026
```

A successful response looks like:

```json
{"id": 12345, "callback_url": "https://YOUR-WORKER.workers.dev", ...}
```

---

## Step 5 — Verify the subscription

```bash
curl -G https://www.strava.com/api/v3/push_subscriptions \
  -d client_id=206570 \
  -d client_secret=98afb2de9c8f69e2b3c05b0f1bff1010e33e2e97
```

You should see your webhook listed with its `id` and `callback_url`.

---

## How it works

```
Patrick finishes run
       ↓
   Strava fires POST to Worker
       ↓
   Worker checks object_type=activity & aspect_type=create
       ↓
   Worker calls GitHub repository_dispatch → event_type: strava-activity
       ↓
   .github/workflows/sync-strava.yml triggers
       ↓
   sync_strava.py runs → data/runs.json updated → dashboard refreshes
```

---

## Troubleshooting

- **403 on verification**: `STRAVA_VERIFY_TOKEN` doesn't match — check it's exactly `patrick-strava-2026`.
- **502 on activity**: Check `GH_PAT` has `repo` and `workflow` scopes; run `gh auth token` to get a fresh one.
- **Logs**: In the Cloudflare dashboard, go to Workers → your worker → **Logs** tab for real-time logs.
