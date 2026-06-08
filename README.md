# creator-auth

Workspace directory service for Hermes Creator Desktop.

This service is intentionally small and dependency-light for the initial CentOS
7.9 deployment. It uses Python's standard library plus SQLite.

## What It Does

- Serves a public workspace manifest at `GET /workspaces`.
- Stores workspace/tenant records with profile names and Hermes gateway URLs.
- Lets Hermes Creator Desktop load a workspace picker before booting a gateway.
- Keeps the previous WeChat/session/admin APIs available for a future auth phase.
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
curl http://127.0.0.1:8088/workspaces
```

## Environment

See [.env.example](.env.example).

Required for production workspace directory mode:

- `CREATOR_AUTH_SECRET`
- `CREATOR_AUTH_ADMIN_TOKEN`

Optional for a later WeChat login phase:

- `WECHAT_APP_ID`
- `WECHAT_APP_SECRET`
- `WECHAT_REDIRECT_URI`

For local smoke tests you can set `CREATOR_AUTH_ALLOW_DEV_LOGIN=1` and use
`POST /dev/login` to create a session without WeChat.

## Deployment

CentOS 7.9 target:

- Host: `47.114.95.173`
- Current public workspace URL: `http://47.114.95.173:8088/workspaces`
- Planned HTTPS workspace URL: `https://yongshengxingda.com/workspaces`
- Recommended install dir: `/opt/creator-auth`
- Recommended data dir: `/var/lib/creator-auth`
- Service: `creator-auth.service`

Use [deploy/centos7-runbook.md](deploy/centos7-runbook.md).
Use [deploy/hermes-dashboard-basic-auth.md](deploy/hermes-dashboard-basic-auth.md)
for the remote Hermes gateway side of the password sign-in MVP.
Use [deploy/wechat-open-platform-setup.md](deploy/wechat-open-platform-setup.md)
only if the project re-enables WeChat login later.

The workspace manifest exposes `authMode: "oauth"` and gateway URLs only.
Creator Desktop uses that mode to open the official Hermes gateway sign-in
window. For the MVP, each remote Hermes dashboard should be configured with the
bundled Basic Auth provider:

```bash
HERMES_DASHBOARD_BASIC_AUTH_USERNAME='creator-name'
HERMES_DASHBOARD_BASIC_AUTH_PASSWORD='change-me'
HERMES_DASHBOARD_BASIC_AUTH_SECRET='32-plus-random-bytes'
HERMES_DASHBOARD_PUBLIC_URL='https://claudewiki.cn/hermes'
```

Use `HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH` instead of plaintext passwords
for production. Dashboard usernames, passwords, hashes, and secrets must not be
stored in creator-auth or returned by `GET /workspaces`.
