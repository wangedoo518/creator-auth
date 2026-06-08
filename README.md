# creator-auth

Central tenant directory and WeChat login service for Hermes Creator Desktop.

This service is intentionally small and dependency-light for the initial CentOS
7.9 deployment. It uses Python's standard library plus SQLite.

## What It Does

- Starts WeChat desktop QR login sessions.
- Handles WeChat OAuth callbacks.
- Stores users, tenants, tenant memberships, desktop sessions, and audit events.
- Returns the tenants a signed-in Desktop user can access.
- Mints short-lived gateway tickets for a tenant.
- Provides admin APIs to create users, tenants, and memberships.

It does not run Hermes agent tasks. Each tenant still has its own Hermes gateway.

## Quick Start

```bash
cp .env.example .env
python3 -m creator_auth.server
```

Health check:

```bash
curl http://127.0.0.1:8088/health
```

## Environment

See [.env.example](.env.example).

Required for production:

- `CREATOR_AUTH_SECRET`
- `CREATOR_AUTH_ADMIN_TOKEN`
- `WECHAT_APP_ID`
- `WECHAT_APP_SECRET`
- `WECHAT_REDIRECT_URI`

For local smoke tests you can set `CREATOR_AUTH_ALLOW_DEV_LOGIN=1` and use
`POST /dev/login` to create a session without WeChat.

## Deployment

CentOS 7.9 target:

- Host: `47.114.95.173`
- Public URL: `https://yongshengxingda.com`
- WeChat callback: `https://yongshengxingda.com/auth/wechat/callback`
- Recommended install dir: `/opt/creator-auth`
- Recommended data dir: `/var/lib/creator-auth`
- Service: `creator-auth.service`

Use [deploy/centos7-runbook.md](deploy/centos7-runbook.md).
Use [deploy/wechat-open-platform-setup.md](deploy/wechat-open-platform-setup.md)
for the WeChat Open Platform website app setup.
