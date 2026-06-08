# WeChat Open Platform Setup

Target service:

- Public domain: `https://yongshengxingda.com`
- OAuth callback URL: `https://yongshengxingda.com/auth/wechat/callback`
- Authorized callback domain: `yongshengxingda.com`

## Prerequisites

- `yongshengxingda.com` and `www.yongshengxingda.com` A records point to
  `47.114.95.173`.
- HTTPS is active for `https://yongshengxingda.com`.
- The edge proxy routes creator-auth API paths to `127.0.0.1:8088`.

WeChat website login will not be production-ready until the callback URL is
publicly reachable over HTTPS.

## Create Website App

1. Open `https://open.weixin.qq.com/` and sign in to the WeChat Open Platform.
2. Go to management center, then website applications.
3. Create or edit the website app for Hermes Creator Desktop login.
4. Set the website domain to `https://yongshengxingda.com`.
5. Set the authorized callback domain to `yongshengxingda.com`.
6. Submit for review if the Open Platform requires approval.
7. Copy the website app `APP_ID` and `APP_SECRET`.

## Configure creator-auth

Edit `/etc/creator-auth/creator-auth.env` on the ECS:

```dotenv
CREATOR_AUTH_PUBLIC_BASE_URL=https://yongshengxingda.com
WECHAT_APP_ID=REPLACE_WITH_WECHAT_OPEN_PLATFORM_APP_ID
WECHAT_APP_SECRET=REPLACE_WITH_WECHAT_OPEN_PLATFORM_APP_SECRET
WECHAT_REDIRECT_URI=https://yongshengxingda.com/auth/wechat/callback
```

Restart and verify:

```bash
systemctl restart creator-auth
systemctl is-active creator-auth
curl -fsS https://yongshengxingda.com/health
```

## Desktop Login Smoke Test

Start a desktop login session:

```bash
curl -fsS -X POST https://yongshengxingda.com/auth/wechat/desktop/start \
  -H 'Content-Type: application/json' \
  -d '{}'
```

The response should include:

- `loginId`
- `expiresAt`
- `authUrl`

Open `authUrl`, complete the WeChat scan, then poll:

```bash
curl -fsS 'https://yongshengxingda.com/auth/wechat/desktop/poll?loginId=REPLACE_WITH_LOGIN_ID'
```

After success, Desktop uses the returned session token to call:

- `GET /me`
- `GET /me/tenants`
- `POST /tenants/lufei/gateway-ticket`
- `POST /tenants/career-coach/gateway-ticket`

## User And Tenant Access

The WeChat callback creates or updates the user account from WeChat identity.
Grant tenant access through the admin API after the user exists:

```bash
curl -fsS -X PUT \
  -H "X-Admin-Token: $CREATOR_AUTH_ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"role":"owner"}' \
  https://yongshengxingda.com/admin/tenants/lufei/members/REPLACE_WITH_USER_ID
```

Use the same pattern for `career-coach` when the same operator should access
both tenant gateways.

