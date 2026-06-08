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

## Security Group

TCP `8088/8088` is open on security group `sg-bp1dy1p5vhdfjs0bbo2x` for initial Desktop integration testing.

Before production, put the service behind HTTPS and restrict or close direct `8088`
public access.

## Seeded Tenants

Current seeded tenant records:

```json
[
  {
    "id": "lufei",
    "profile": "lufei-creator-profile",
    "displayName": "路飞设计沉思录",
    "gatewayUrl": "https://lufei.example.com/hermes"
  },
  {
    "id": "career-coach",
    "profile": "career-coach-copilot",
    "displayName": "求职咨询助手",
    "gatewayUrl": "https://career.example.com/hermes"
  }
]
```

Replace placeholder gateway URLs after the tenant Hermes gateways have HTTPS
domains.

## Bootstrap User

A placeholder bootstrap owner user was created and granted `owner` on both
seeded tenants. Replace this with real WeChat-bound users when WeChat Open
Platform credentials are available.

## Pending Production Inputs

- Real domain for creator-auth, for example `https://auth.example.com`.
- HTTPS certificate and reverse proxy.
- WeChat Open Platform website app:
  - `WECHAT_APP_ID`
  - `WECHAT_APP_SECRET`
  - registered callback URL, for example `https://auth.example.com/auth/wechat/callback`
- Real tenant gateway URLs:
  - lufei gateway domain
  - career-coach gateway domain
- Hermes gateway support for validating creator-auth gateway tickets.

## Verification Commands

```bash
curl -fsS http://47.114.95.173:8088/health

ssh root@47.114.95.173 'systemctl is-active creator-auth'
ssh root@47.114.95.173 'cd /opt/creator-auth && python3 -m unittest discover -s tests -p "test_*.py"'
```

