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
Use [deploy/wechat-open-platform-setup.md](deploy/wechat-open-platform-setup.md)
only if the project re-enables WeChat login later.

The workspace manifest exposes `authMode: "token"` and gateway URLs only. It
must not expose Hermes dashboard tokens; Creator Desktop asks the creator for
the workspace token on first bind and stores it locally.
