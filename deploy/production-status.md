# Production Deployment Status

Last updated: 2026-06-09

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
for preparation but cannot bind port 80 while that container is active; the
current `nginx.service` status is failed and does not affect the direct
`0.0.0.0:8088` creator-auth service.

Production HTTPS requires one of these choices:

- Add creator-auth routes to the existing `zrimg-web` Nginx edge.
- Move the existing `zrimg-web` public port and let system Nginx own 80/443.
- Deploy creator-auth behind a separate ECS, load balancer, or auth subdomain.

## Seeded Tenants

Current seeded tenant records for the workspace picker MVP:

```json
[
  {
    "id": "lufei",
    "profile": "lufei-creator-profile",
    "displayName": "路飞设计沉思录",
    "gatewayUrl": "http://124.220.29.171:9119",
    "authMode": "oauth"
  },
  {
    "id": "career-coach",
    "profile": "career-coach-copilot",
    "displayName": "求职咨询助手",
    "gatewayUrl": "http://43.143.118.134:9119",
    "authMode": "oauth"
  }
]
```

`http://47.114.95.173:8088/workspaces` now returns these records. The URLs are
the direct Tencent Cloud Hermes dashboard ports for
trusted-network pilot use. They are intentionally distinct per profile:

- `lufei-creator-profile` runs on Tencent Lighthouse `124.220.29.171`.
- `career-coach-copilot` runs on Tencent CVM `43.143.118.134`.

The previously used `https://claudewiki.cn/hermes` URL is not a valid workspace
Remote URL for this MVP: `claudewiki.cn/v1` is the model provider endpoint, and
the `/hermes` path currently serves another app unless a dedicated Hermes
dashboard reverse proxy is added later.

## Workspace + Password Sign-In Desktop Flow

Hermes Creator Desktop now loads `GET /workspaces`, shows a workspace picker,
saves the selected workspace as a per-profile remote override with
`authMode: "oauth"`, then opens the official Hermes dashboard sign-in window.
For the MVP, each remote Hermes dashboard uses the bundled Basic Auth provider,
so the window renders a username/password form. Users never paste a Session
Token. WeChat login, creator-auth users, memberships, and custom gateway
tickets are not part of the MVP path. Dashboard credentials and auth secrets are
stored only on the remote Hermes dashboard host, not in creator-auth.

## Pending Production Inputs

- DNS A records for `yongshengxingda.com` and `www.yongshengxingda.com` pointing
  to `47.114.95.173`.
- HTTPS certificate and reverse proxy for `https://yongshengxingda.com`.
- `lufei` Hermes dashboard at `http://124.220.29.171:9119` is running on the
  Tencent host with Basic Auth enabled, but the public Tencent Lighthouse
  firewall/security group still needs to allow `9119/tcp`.
- `career-coach` Hermes dashboard at `http://43.143.118.134:9119` has
  dashboard auth secrets/variables configured in GitHub; it still needs
  `TENCENT_CVM_SSH_PRIVATE_KEY`, deployment, and public `9119/tcp` access.
- Public distribution still needs HTTPS or VPN access control for both Remote
  URLs. Direct HTTP on port `9119` is suitable only for trusted-network pilots.

As of 2026-06-09, `lufei` has passed server-local `/api/status` and
`/api/auth/providers` checks with `auth_required=true` and provider `basic`.
The same check from GitHub runner and from the Tencent host to its own public IP
still times out, which points to the cloud firewall/security group. End-to-end
Desktop sign-in cannot be considered complete until both dashboard public
Remote URLs can reach `/api/status`, `/api/auth/providers`, `/login`, and the
WebSocket ticket flow.

## Verification Commands

```bash
curl -fsS http://47.114.95.173:8088/health
curl -fsS http://47.114.95.173:8088/workspaces
curl -fsS http://124.220.29.171:9119/api/status
curl -fsS http://43.143.118.134:9119/api/status

ssh root@47.114.95.173 'systemctl is-active creator-auth'
ssh root@47.114.95.173 'cd /opt/creator-auth && python3 -m unittest discover -s tests -p "test_*.py"'
```
