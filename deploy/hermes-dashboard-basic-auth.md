# Hermes Dashboard Basic Auth Gateway

This is the required gateway side for the workspace picker + password sign-in
MVP. Creator-auth only publishes the workspace directory; it does not store or
verify Hermes dashboard passwords.

## Runtime Contract

Each creator workspace needs a Hermes dashboard URL that serves the official
dashboard API and auth routes:

- `GET /api/status` returns Hermes status JSON with `auth_required: true`.
- `GET /api/auth/providers` lists a provider with `supports_password: true`.
- `GET /login` renders the Hermes sign-in page.
- `POST /auth/password-login` sets dashboard session cookies.
- `GET /api/ws-ticket` mints a one-shot WebSocket ticket after sign-in.
- `GET /api/ws?ticket=...` accepts Desktop WebSocket traffic.

For the current pilot both workspace records point to
`https://claudewiki.cn/hermes`. That URL must route to Hermes dashboard, not to
Sub2API or another app.

## Required Hermes Environment

Configure these on the remote Hermes dashboard process:

```bash
HERMES_DASHBOARD_BASIC_AUTH_USERNAME='creator-name'
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH='scrypt$...'
HERMES_DASHBOARD_BASIC_AUTH_SECRET='32-plus-random-bytes'
HERMES_DASHBOARD_PUBLIC_URL='https://claudewiki.cn/hermes'
```

Use `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD` only for temporary smoke tests.
Generate the preferred hash from the Hermes Agent source/runtime:

```bash
python3 -c "from plugins.dashboard_auth.basic import hash_password; print(hash_password('REPLACE_WITH_PASSWORD'))"
```

Start the dashboard bound to a non-loopback host without `--insecure` so the
auth gate is enabled:

```bash
hermes dashboard --host 0.0.0.0 --port 9119 --no-open
```

If Docker/s6 is used, set `HERMES_DASHBOARD=1`,
`HERMES_DASHBOARD_HOST=0.0.0.0`, and `HERMES_DASHBOARD_PORT=9119`; do not set
`HERMES_DASHBOARD_INSECURE`.

## Reverse Proxy Checks

The reverse proxy must preserve the `/hermes` path prefix and forward WebSocket
upgrade requests. After deployment, these probes should pass:

```bash
curl -fsS https://claudewiki.cn/hermes/api/status
curl -fsS https://claudewiki.cn/hermes/api/auth/providers
curl -I https://claudewiki.cn/hermes/login
```

Expected signs:

- `/api/status` is JSON, not HTML.
- `auth_required` is `true`.
- `/api/auth/providers` contains the `basic` provider.
- `/login` is the Hermes dashboard login page.
