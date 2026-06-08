#!/usr/bin/env bash
set -euo pipefail

HOST="${CREATOR_AUTH_DEPLOY_HOST:-root@47.114.95.173}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

ssh "$HOST" <<'EOF'
set -euo pipefail
yum install -y python3 rsync
id creator-auth >/dev/null 2>&1 || useradd --system --home-dir /opt/creator-auth --shell /sbin/nologin creator-auth
mkdir -p /opt/creator-auth /etc/creator-auth /var/lib/creator-auth
chown -R creator-auth:creator-auth /opt/creator-auth /var/lib/creator-auth
chmod 750 /etc/creator-auth
EOF

rsync -az --delete \
  --no-owner \
  --no-group \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  "$ROOT/" "$HOST:/opt/creator-auth/"

scp "$ROOT/deploy/systemd/creator-auth.service" "$HOST:/etc/systemd/system/creator-auth.service"

ssh "$HOST" <<'EOF'
set -euo pipefail
if [ ! -f /etc/creator-auth/creator-auth.env ]; then
  cp /opt/creator-auth/.env.example /etc/creator-auth/creator-auth.env
  echo "Created /etc/creator-auth/creator-auth.env; edit secrets before starting the service." >&2
  exit 2
fi
chown root:creator-auth /etc/creator-auth/creator-auth.env
chmod 640 /etc/creator-auth/creator-auth.env
chown -R root:root /opt/creator-auth
chown -R creator-auth:creator-auth /var/lib/creator-auth
systemctl daemon-reload
systemctl enable --now creator-auth
systemctl status creator-auth --no-pager
curl -fsS http://127.0.0.1:8088/health
EOF
