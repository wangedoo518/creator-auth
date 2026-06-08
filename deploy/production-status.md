# Production Deployment Status

Last updated: 2026-06-08

## Server

- Cloud: Alibaba Cloud ECS
- Region: `cn-hangzhou`
- Instance ID: `i-bp1dy1p5vhdfjs05e1hs`
- Hostname: `iZbp1dy1p5vhdfjs05e1hsZ`
- Public IP: `47.114.95.173`
- OS: CentOS Linux 7.9.2009
- Runtime: Python 3.6.8

## Deployed Service

- Service name: `creator-auth.service`
- Install dir: `/opt/creator-auth`
- Env file: `/etc/creator-auth/creator-auth.env`
- Data dir: `/var/lib/creator-auth`
- SQLite DB: `/var/lib/creator-auth/creator-auth.db`
- Listen address: `0.0.0.0:8088`
- Public health URL: `http://47.114.95.173:8088/health`
- Public workspace URL: `http://47.114.95.173:8088/workspaces`
- Planned HTTPS URL: `https://yongshengxingda.com`
- Planned HTTPS workspace URL: `https://yongshengxingda.com/workspaces`

`yongshengxingda.com` and `www.yongshengxingda.com` did not return A records
when checked on 2026-06-08, so HTTPS certificate issuance is blocked until DNS
points to `47.114.95.173`.

## Security Group

TCP `8088/8088` is open on security group `sg-bp1dy1p5vhdfjs0bbo2x` for initial Desktop integration testing.
TCP `80/80` and `443/443` have also been opened for the planned HTTPS rollout.

Before production, put the service behind HTTPS, then restrict or close direct
`8088` public access.

## Edge Routing Status

Port 80 on the ECS is already owned by the existing Docker service
`zrimg-web-1`, which serves an Nginx static web app. System Nginx was installed
for preparation but left disabled because it cannot bind port 80 while that
container is active.

Production HTTPS requires one of these choices:

- Add creator-auth routes to the existing `zrimg-web` Nginx edge.
- Move the existing `zrimg-web` public port and let system Nginx own 80/443.
- Deploy creator-auth behind a separate ECS, load balancer, or auth subdomain.

## Seeded Tenants

Current seeded tenant records:

```json
[
  {
    "id": "lufei",
    "profile": "lufei-creator-profile",
    "displayName": "路飞设计沉思录",
    "gatewayUrl": "https://claudewiki.cn/hermes",
    "authMode": "none"
  },
  {
    "id": "career-coach",
    "profile": "career-coach-copilot",
    "displayName": "求职咨询助手",
    "gatewayUrl": "https://claudewiki.cn/hermes",
    "authMode": "none"
  }
]
```

Both tenants currently share the `claudewiki.cn` Hermes gateway domain. If the
gateway later exposes tenant-specific paths or subdomains, update the two tenant
records through the admin API.

## No-login Desktop Flow

Hermes Creator Desktop now loads `GET /workspaces`, shows a workspace picker,
and saves the selected workspace as a per-profile remote override with
`authMode: "none"`. WeChat login, users, memberships, and gateway tickets are
not part of the MVP path.

## Pending Production Inputs

- DNS A records for `yongshengxingda.com` and `www.yongshengxingda.com` pointing
  to `47.114.95.173`.
- HTTPS certificate and reverse proxy for `https://yongshengxingda.com`.
- Hermes gateway at `https://claudewiki.cn/hermes` must accept no-login Desktop
  REST and WebSocket traffic for the configured workspaces.

## Verification Commands

```bash
curl -fsS http://47.114.95.173:8088/health
curl -fsS http://47.114.95.173:8088/workspaces

ssh root@47.114.95.173 'systemctl is-active creator-auth'
ssh root@47.114.95.173 'cd /opt/creator-auth && python3 -m unittest discover -s tests -p "test_*.py"'
```
