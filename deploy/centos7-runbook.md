# CentOS 7.9 Deployment Runbook

Target server:

- Instance: `i-bp1dy1p5vhdfjs05e1hs`
- Hostname: `iZbp1dy1p5vhdfjs05e1hsZ`
- Region: 华东1（杭州）
- Public IP: `47.114.95.173`
- OS: CentOS 7.9 64-bit
- Size: 2 vCPU / 2 GiB

## 1. SSH Access

The current local machine does not have working SSH access yet:

```text
root@47.114.95.173: Permission denied (publickey,gssapi-keyex,gssapi-with-mic,password).
```

Add the operator public key in the Alibaba Cloud console or provide an SSH user/key,
then verify:

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
CREATOR_AUTH_PUBLIC_BASE_URL=https://auth.example.com
CREATOR_AUTH_DB=/var/lib/creator-auth/creator-auth.db
CREATOR_AUTH_SECRET=REPLACE_WITH_RANDOM_SECRET
CREATOR_AUTH_ADMIN_TOKEN=REPLACE_WITH_RANDOM_ADMIN_TOKEN
WECHAT_APP_ID=REPLACE_WITH_WECHAT_OPEN_PLATFORM_APP_ID
WECHAT_APP_SECRET=REPLACE_WITH_WECHAT_OPEN_PLATFORM_APP_SECRET
WECHAT_REDIRECT_URI=https://auth.example.com/auth/wechat/callback
CREATOR_AUTH_ALLOW_DEV_LOGIN=0
```

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
https://auth.example.com
```

Minimal Nginx location:

```nginx
server {
  listen 443 ssl http2;
  server_name auth.example.com;

  ssl_certificate /etc/letsencrypt/live/auth.example.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/auth.example.com/privkey.pem;

  location / {
    proxy_pass http://127.0.0.1:8088;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

## 7. Seed Tenants

After the service starts:

```bash
export CREATOR_AUTH_BASE_URL=http://127.0.0.1:8088
export CREATOR_AUTH_ADMIN_TOKEN=REPLACE_WITH_RANDOM_ADMIN_TOKEN
python3 scripts/seed_tenants.py
```

Before production, replace placeholder gateway URLs:

- `https://lufei.example.com/hermes`
- `https://career.example.com/hermes`

with the real gateway domains.

## 8. Smoke Tests

```bash
curl -fsS https://auth.example.com/health

curl -fsS -H "X-Admin-Token: $CREATOR_AUTH_ADMIN_TOKEN" \
  https://auth.example.com/admin/tenants
```

For local development only:

```bash
CREATOR_AUTH_ALLOW_DEV_LOGIN=1 python3 -m creator_auth.server
curl -s -X POST http://127.0.0.1:8088/dev/login \
  -H 'Content-Type: application/json' \
  -d '{"unionId":"dev-union","openId":"dev-open","nickname":"Dev"}'
```
