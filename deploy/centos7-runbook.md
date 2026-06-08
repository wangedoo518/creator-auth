# CentOS 7.9 Deployment Runbook

Target server:

- Instance: `i-bp1dy1p5vhdfjs05e1hs`
- Hostname: `iZbp1dy1p5vhdfjs05e1hsZ`
- Region: 华东1（杭州）
- Public IP: `47.114.95.173`
- OS: CentOS 7.9 64-bit
- Size: 2 vCPU / 2 GiB

## 1. SSH Access

SSH access is enabled for the current operator key. Verify with:

```bash
ssh root@47.114.95.173 'hostname; whoami; cat /etc/centos-release'
```

## 2. Install Runtime

```bash
ssh root@47.114.95.173 <<'EOF'
set -euo pipefail
yum install -y python3 rsync
id creator-auth >/dev/null 2>&1 || useradd --system --home-dir /opt/creator-auth --shell /sbin/nologin creator-auth
mkdir -p /opt/creator-auth /etc/creator-auth /var/lib/creator-auth
chown -R creator-auth:creator-auth /opt/creator-auth /var/lib/creator-auth
chmod 750 /etc/creator-auth
EOF
```

If `yum install python3` is unavailable, enable EPEL or install Python 3.8+ from
the provider image. The service uses only the Python standard library.

## 3. Sync Code

From the local repository:

```bash
cd /Users/champion/Documents/develop/farm/creator-auth
rsync -az --delete \
  --no-owner \
  --no-group \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  ./ root@47.114.95.173:/opt/creator-auth/
```

## 4. Configure Environment

Create `/etc/creator-auth/creator-auth.env`:

```dotenv
CREATOR_AUTH_HOST=127.0.0.1
CREATOR_AUTH_PORT=8088
CREATOR_AUTH_PUBLIC_BASE_URL=https://yongshengxingda.com
CREATOR_AUTH_DB=/var/lib/creator-auth/creator-auth.db
CREATOR_AUTH_SECRET=REPLACE_WITH_RANDOM_SECRET
CREATOR_AUTH_ADMIN_TOKEN=REPLACE_WITH_RANDOM_ADMIN_TOKEN
WECHAT_APP_ID=REPLACE_WITH_WECHAT_OPEN_PLATFORM_APP_ID
WECHAT_APP_SECRET=REPLACE_WITH_WECHAT_OPEN_PLATFORM_APP_SECRET
WECHAT_REDIRECT_URI=https://yongshengxingda.com/auth/wechat/callback
CREATOR_AUTH_ALLOW_DEV_LOGIN=0
```

For the workspace picker + password sign-in MVP, `WECHAT_APP_ID`,
`WECHAT_APP_SECRET`, and `WECHAT_REDIRECT_URI` may remain empty.

Generate secrets locally:

```bash
python3 - <<'PY'
import secrets
print("CREATOR_AUTH_SECRET=" + secrets.token_urlsafe(48))
print("CREATOR_AUTH_ADMIN_TOKEN=" + secrets.token_urlsafe(32))
PY
```

Secure the env file:

```bash
ssh root@47.114.95.173 'chown root:creator-auth /etc/creator-auth/creator-auth.env && chmod 640 /etc/creator-auth/creator-auth.env'
```

Normalize code/data ownership:

```bash
ssh root@47.114.95.173 'chown -R root:root /opt/creator-auth && chown -R creator-auth:creator-auth /var/lib/creator-auth'
```

## 5. Install systemd Unit

```bash
scp deploy/systemd/creator-auth.service root@47.114.95.173:/etc/systemd/system/creator-auth.service
ssh root@47.114.95.173 <<'EOF'
set -euo pipefail
systemctl daemon-reload
systemctl enable --now creator-auth
systemctl status creator-auth --no-pager
curl -fsS http://127.0.0.1:8088/health
EOF
```

## 6. Nginx Reverse Proxy

Recommended public URL:

```text
https://yongshengxingda.com
```

Before issuing the certificate, point `yongshengxingda.com` and
`www.yongshengxingda.com` A records to `47.114.95.173`, then open ports 80 and
443 in the ECS security group.

On the current ECS, port 80 is already served by the existing Docker container
`zrimg-web-1`. Do not start system Nginx on 80/443 until the edge routing
ownership is decided. Use one of these approaches:

- Add creator-auth API routes to the existing `zrimg-web` Nginx edge.
- Move `zrimg-web` to another public port and let system Nginx own 80/443.
- Put creator-auth on a separate ECS, load balancer, or auth subdomain.

If reusing the existing Docker edge, add this to the `web` service in
`/opt/zrimg/deploy/docker-compose.yml`:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

Then add these locations before the SPA fallback in the `zrimg-web` Nginx
template:

```nginx
location = /health { proxy_pass http://host.docker.internal:8088; }
location /auth/ { proxy_pass http://host.docker.internal:8088; }
location = /me { proxy_pass http://host.docker.internal:8088; }
location /me/ { proxy_pass http://host.docker.internal:8088; }
location /tenants/ { proxy_pass http://host.docker.internal:8088; }
location /admin/ { proxy_pass http://host.docker.internal:8088; }
```

Install Nginx and Certbot, then start with the HTTP bootstrap config:

```bash
yum install -y epel-release
yum install -y nginx certbot
mkdir -p /var/www/certbot /etc/nginx/conf.d
cp /opt/creator-auth/deploy/nginx/creator-auth-http-bootstrap.conf /etc/nginx/conf.d/creator-auth.conf
nginx -t && systemctl enable --now nginx
```

After DNS points to `47.114.95.173`, request the certificate and switch to the
final HTTPS reverse proxy config:

```bash
certbot certonly --webroot \
  -w /var/www/certbot \
  -d yongshengxingda.com \
  -d www.yongshengxingda.com
cp /opt/creator-auth/deploy/nginx/creator-auth.conf /etc/nginx/conf.d/creator-auth.conf
nginx -t && systemctl reload nginx
```

## 7. Seed Tenants

After the service starts:

```bash
export CREATOR_AUTH_BASE_URL=http://127.0.0.1:8088
export CREATOR_AUTH_ADMIN_TOKEN=REPLACE_WITH_RANDOM_ADMIN_TOKEN
python3 scripts/seed_tenants.py
```

Default production gateway URLs:

- `https://claudewiki.cn/hermes`
- `https://claudewiki.cn/hermes`

If the two tenants later move to separate gateway paths or subdomains, update
their tenant records with the admin API and rerun the Desktop smoke tests.

The public Desktop manifest is available without login:

```bash
curl -fsS http://127.0.0.1:8088/workspaces
```

The manifest should show `authMode: "oauth"` for each workspace. Do not put
Hermes dashboard usernames, password hashes, plaintext passwords, or Basic Auth
secrets in creator-auth or in the public manifest. Configure those values on
each remote Hermes dashboard:

```bash
HERMES_DASHBOARD_BASIC_AUTH_USERNAME='creator-name'
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH='scrypt$...'
HERMES_DASHBOARD_BASIC_AUTH_SECRET='32-plus-random-bytes'
HERMES_DASHBOARD_PUBLIC_URL='https://claudewiki.cn/hermes'
```

## 8. Smoke Tests

```bash
curl -fsS https://yongshengxingda.com/health
curl -fsS https://yongshengxingda.com/workspaces

curl -fsS -H "X-Admin-Token: $CREATOR_AUTH_ADMIN_TOKEN" \
  https://yongshengxingda.com/admin/tenants
```

For local development only:

```bash
CREATOR_AUTH_ALLOW_DEV_LOGIN=1 python3 -m creator_auth.server
curl -s -X POST http://127.0.0.1:8088/dev/login \
  -H 'Content-Type: application/json' \
  -d '{"unionId":"dev-union","openId":"dev-open","nickname":"Dev"}'
```
