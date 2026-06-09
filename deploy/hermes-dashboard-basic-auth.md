# Hermes Dashboard Basic Auth Gateway

This is the required gateway side for the workspace picker + password sign-in
MVP. Creator-auth only publishes the workspace directory; it does not store or
verify Hermes dashboard passwords.

## Runtime Contract

Each creator workspace needs a Hermes dashboard URL that serves the official
dashboard API and auth routes. This is separate from the profile gateway
service named `hermes-gateway-*`; Desktop Remote URL talks to the dashboard
REST/WebSocket surface.

- `GET /api/status` returns Hermes status JSON with `auth_required: true`.
- `GET /api/auth/providers` lists a provider with `supports_password: true`.
- `GET /login` renders the Hermes sign-in page.
- `POST /auth/password-login` sets dashboard session cookies.
- `POST /api/auth/ws-ticket` mints a one-shot WebSocket ticket after sign-in.
- `GET /api/ws?ticket=...` accepts Desktop WebSocket traffic.

Current trusted-network pilot workspace URLs:

| workspace | profile | Tencent host | dashboard Remote URL |
| --- | --- | --- | --- |
| `lufei` | `lufei-creator-profile` | `124.220.29.171` | `http://124.220.29.171:9119` |
| `career-coach` | `career-coach-copilot` | `43.143.118.134` | `http://43.143.118.134:9119` |

`claudewiki.cn/v1` remains the model provider endpoint in the profile `.env`.
It is not the Desktop dashboard Remote URL unless an explicit reverse proxy is
later configured for it.

## Required Hermes Environment

Configure these on the remote Hermes dashboard process:

```bash
HERMES_DASHBOARD_BASIC_AUTH_USERNAME='creator-name'
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH='scrypt$...'
HERMES_DASHBOARD_BASIC_AUTH_SECRET='32-plus-random-bytes'
HERMES_DASHBOARD_PUBLIC_URL='http://124.220.29.171:9119'
```

Use `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD` only for temporary smoke tests.
Generate the preferred hash from the Hermes Agent source/runtime:

```bash
python3 -c "from plugins.dashboard_auth.basic import hash_password; print(hash_password('REPLACE_WITH_PASSWORD'))"
```

Start the dashboard bound to a non-loopback host without `--insecure` so the
auth gate is enabled:

```bash
hermes -p lufei-creator-profile dashboard --host 0.0.0.0 --port 9119 --no-open
```

If Docker/s6 is used, set `HERMES_DASHBOARD=1`,
`HERMES_DASHBOARD_HOST=0.0.0.0`, and `HERMES_DASHBOARD_PORT=9119`; do not set
`HERMES_DASHBOARD_INSECURE`.

## Tencent Cloud Systemd User Service

Run one dashboard process per Tencent profile machine. Keep the password hash
and secret in a server-local env file, not in creator-auth.

Lufei Lighthouse:

```bash
ssh lufei-tencent <<'EOF'
set -euo pipefail

profile=lufei-creator-profile
env_dir="$HOME/.config/hermes-dashboard"
service_dir="$HOME/.config/systemd/user"
env_file="$env_dir/$profile.env"
service_file="$service_dir/hermes-dashboard-$profile.service"

install -d -m 700 "$env_dir" "$service_dir"

cat > "$env_file" <<'ENV'
HERMES_DASHBOARD_BASIC_AUTH_USERNAME=lufei
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH=REPLACE_WITH_SCRYPT_HASH
HERMES_DASHBOARD_BASIC_AUTH_SECRET=REPLACE_WITH_32_PLUS_RANDOM_BYTES
HERMES_DASHBOARD_PUBLIC_URL=http://124.220.29.171:9119
ENV
chmod 600 "$env_file"

cat > "$service_file" <<SERVICE
[Unit]
Description=Hermes dashboard for $profile
After=network-online.target

[Service]
Type=simple
EnvironmentFile=$env_file
ExecStart=/usr/local/bin/hermes -p $profile dashboard --host 0.0.0.0 --port 9119 --no-open
Restart=always
RestartSec=5
WorkingDirectory=$HOME/.hermes/profiles/$profile

[Install]
WantedBy=default.target
SERVICE

systemctl --user daemon-reload
systemctl --user enable --now "hermes-dashboard-$profile.service"
systemctl --user status "hermes-dashboard-$profile.service" --no-pager
EOF
```

Career Coach CVM:

```bash
ssh career-copilot-cvm <<'EOF'
set -euo pipefail

profile=career-coach-copilot
env_dir="$HOME/.config/hermes-dashboard"
service_dir="$HOME/.config/systemd/user"
env_file="$env_dir/$profile.env"
service_file="$service_dir/hermes-dashboard-$profile.service"

install -d -m 700 "$env_dir" "$service_dir"

cat > "$env_file" <<'ENV'
HERMES_DASHBOARD_BASIC_AUTH_USERNAME=career-coach
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH=REPLACE_WITH_SCRYPT_HASH
HERMES_DASHBOARD_BASIC_AUTH_SECRET=REPLACE_WITH_32_PLUS_RANDOM_BYTES
HERMES_DASHBOARD_PUBLIC_URL=http://43.143.118.134:9119
ENV
chmod 600 "$env_file"

cat > "$service_file" <<SERVICE
[Unit]
Description=Hermes dashboard for $profile
After=network-online.target

[Service]
Type=simple
EnvironmentFile=$env_file
ExecStart=/usr/local/bin/hermes -p $profile dashboard --host 0.0.0.0 --port 9119 --no-open
Restart=always
RestartSec=5
WorkingDirectory=$HOME/.hermes/profiles/$profile

[Install]
WantedBy=default.target
SERVICE

systemctl --user daemon-reload
systemctl --user enable --now "hermes-dashboard-$profile.service"
systemctl --user status "hermes-dashboard-$profile.service" --no-pager
EOF
```

If `hermes dashboard` exits because `fastapi`, `uvicorn`, or the web bundle is
missing, upgrade/install the Hermes Agent runtime on that machine before
enabling the service. The career CVM deployment doc currently records Hermes
`v0.12.0`; verify that version includes the dashboard command and Basic Auth
provider before rollout.

## Reverse Proxy Checks

For the current trusted-network pilot, probe the direct dashboard URLs:

```bash
curl -fsS http://124.220.29.171:9119/api/status
curl -fsS http://124.220.29.171:9119/api/auth/providers
curl -I http://124.220.29.171:9119/login

curl -fsS http://43.143.118.134:9119/api/status
curl -fsS http://43.143.118.134:9119/api/auth/providers
curl -I http://43.143.118.134:9119/login
```

Expected signs:

- `/api/status` is JSON, not HTML.
- `auth_required` is `true`.
- `/api/auth/providers` contains the `basic` provider.
- `/login` is the Hermes dashboard login page.

For public production, put each dashboard behind HTTPS or VPN. If using HTTPS
with a path prefix such as `/hermes`, set `HERMES_DASHBOARD_PUBLIC_URL` to the
full public URL and configure the reverse proxy to preserve the prefix and
forward WebSocket upgrades.
