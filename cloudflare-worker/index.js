/**
 * Strava → GitHub Webhook Bridge
 *
 * Environment variables (set in Cloudflare dashboard):
 *   STRAVA_VERIFY_TOKEN  — must match the verify_token you pass to Strava when registering
 *   GH_PAT               — GitHub Personal Access Token with repo + workflow scopes
 */

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // ── GET: Strava webhook verification handshake ──────────────────────────
    if (request.method === 'GET') {
      const mode      = url.searchParams.get('hub.mode');
      const challenge = url.searchParams.get('hub.challenge');
      const token     = url.searchParams.get('hub.verify_token');

      if (mode === 'subscribe' && token === env.STRAVA_VERIFY_TOKEN) {
        return new Response(
          JSON.stringify({ 'hub.challenge': challenge }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        );
      }

      return new Response('Forbidden', { status: 403 });
    }

    // ── POST: Strava activity event ─────────────────────────────────────────
    if (request.method === 'POST') {
      let event;
      try {
        event = await request.json();
      } catch {
        return new Response('Bad Request', { status: 400 });
      }

      // Only trigger sync for brand-new activities
      if (event.object_type === 'activity' && event.aspect_type === 'create') {
        const ghRes = await fetch(
          'https://api.github.com/repos/worapratyy/patrick-running-hub/dispatches',
          {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${env.GH_PAT}`,
              'Accept': 'application/vnd.github+json',
              'Content-Type': 'application/json',
              'User-Agent': 'patrick-strava-webhook/1.0',
            },
            body: JSON.stringify({ event_type: 'strava-activity' }),
          }
        );

        if (!ghRes.ok) {
          const body = await ghRes.text();
          console.error(`GitHub dispatch failed: ${ghRes.status} ${body}`);
          return new Response('GitHub dispatch failed', { status: 502 });
        }

        console.log(`Dispatched strava-activity for activity ${event.object_id}`);
      }

      // Always return 200 to Strava so it doesn't retry
      return new Response('OK', { status: 200 });
    }

    return new Response('Method Not Allowed', { status: 405 });
  },
};
