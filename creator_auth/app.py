import json
import re
import time
from urllib.parse import parse_qs, urlparse

from .config import Settings
from .crypto import random_token, sha256_text, sign_json
from .db import Database, now, row_to_tenant
from .wechat import build_qrconnect_url, exchange_code, fetch_userinfo

TENANT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
ROLE_VALUES = {"owner", "operator", "reviewer", "viewer"}


class HttpError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


class CreatorAuthApp:
    def __init__(self, settings: Settings, db: Database):
        self.settings = settings
        self.db = db

    def handle(self, method, path, headers, body):
        parsed = urlparse(path)
        route = parsed.path.rstrip("/") or "/"
        query = {k: v[-1] for k, v in parse_qs(parsed.query).items()}
        data = self._json_body(body)

        if method == "GET" and route == "/health":
            return self.json({"ok": True, "service": "creator-auth", "time": now()})

        if method == "GET" and route == "/workspaces":
            return self.json(self.public_workspaces())

        if method == "POST" and route == "/auth/wechat/desktop/start":
            return self.json(self.start_wechat_login(data))

        if method == "GET" and route == "/auth/wechat/callback":
            return self.html(self.wechat_callback(query))

        if method == "GET" and route == "/auth/wechat/desktop/poll":
            return self.json(self.poll_wechat_login(query))

        if method == "GET" and route == "/me":
            user = self.require_session(headers)
            return self.json({"user": self.public_user(user)})

        if method == "GET" and route == "/me/tenants":
            user = self.require_session(headers)
            return self.json({"tenants": self.tenants_for_user(user["id"])})

        tenant_ticket_match = re.match(r"^/tenants/([^/]+)/gateway-ticket$", route)
        if method == "POST" and tenant_ticket_match:
            user = self.require_session(headers)
            tenant_id = tenant_ticket_match.group(1)
            return self.json(self.gateway_ticket(user, tenant_id))

        if self.settings.allow_dev_login and method == "POST" and route == "/dev/login":
            return self.json(self.dev_login(data))

        if route.startswith("/admin/"):
            self.require_admin(headers)
            return self.handle_admin(method, route, data)

        raise HttpError(404, "not found")

    def json(self, payload, status=200):
        return status, {"Content-Type": "application/json; charset=utf-8"}, payload

    def html(self, text, status=200):
        return status, {"Content-Type": "text/html; charset=utf-8"}, text

    def _json_body(self, body):
        if not body:
            return {}
        try:
            payload = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise HttpError(400, "invalid json") from exc
        if not isinstance(payload, dict):
            raise HttpError(400, "json body must be an object")
        return payload

    def start_wechat_login(self, data):
        if not self.settings.wechat_app_id or not self.settings.wechat_redirect_uri:
            raise HttpError(500, "wechat login is not configured")

        nonce = random_token("login")
        state = random_token("wxstate")
        device_id = str(data.get("deviceId") or "")
        created_at = now()
        expires_at = created_at + self.settings.login_ttl_seconds
        self.db.execute(
            "INSERT INTO desktop_login_nonces(nonce, state, device_id, created_at, expires_at) VALUES(?,?,?,?,?)",
            (nonce, state, device_id, created_at, expires_at),
        )
        self.db.audit("wechat_login_started", device_id=device_id)
        return {
            "loginNonce": nonce,
            "expiresAt": expires_at,
            "qrconnectUrl": build_qrconnect_url(self.settings.wechat_app_id, self.settings.wechat_redirect_uri, state),
        }

    def wechat_callback(self, query):
        code = query.get("code") or ""
        state = query.get("state") or ""
        if not code or not state:
            raise HttpError(400, "missing code or state")

        nonce_row = self.db.query_one("SELECT * FROM desktop_login_nonces WHERE state=?", (state,))
        if not nonce_row:
            raise HttpError(400, "invalid state")
        if nonce_row["expires_at"] < now():
            raise HttpError(400, "login expired")
        if nonce_row["status"] != "pending":
            return self._callback_html("登录已处理，可以回到 Desktop。")

        token_payload = exchange_code(self.settings.wechat_app_id, self.settings.wechat_app_secret, code)
        access_token = token_payload["access_token"]
        open_id = token_payload["openid"]
        userinfo = fetch_userinfo(access_token, open_id)
        union_id = userinfo.get("unionid") or token_payload.get("unionid") or ""
        user = self.upsert_wechat_user(open_id=open_id, union_id=union_id, userinfo=userinfo)

        completed_at = now()
        self.db.execute(
            "UPDATE desktop_login_nonces SET status='completed', user_id=?, completed_at=? WHERE nonce=?",
            (user["id"], completed_at, nonce_row["nonce"]),
        )
        self.db.audit("wechat_login_completed", actor_user_id=user["id"])
        return self._callback_html("微信登录成功，可以回到 Hermes Creator Desktop。")

    def _callback_html(self, message):
        safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"<!doctype html><meta charset='utf-8'><title>Hermes Creator Desktop</title><p>{safe}</p>"

    def upsert_wechat_user(self, open_id, union_id, userinfo):
        row = None
        if union_id:
            row = self.db.query_one("SELECT * FROM users WHERE wechat_union_id=?", (union_id,))
        if not row:
            row = self.db.query_one("SELECT * FROM users WHERE wechat_open_id=?", (open_id,))

        nickname = str(userinfo.get("nickname") or "")
        avatar_url = str(userinfo.get("headimgurl") or "")
        ts = now()

        if row:
            self.db.execute(
                "UPDATE users SET wechat_union_id=?, wechat_open_id=?, nickname=?, avatar_url=?, last_login_at=? WHERE id=?",
                (union_id or row["wechat_union_id"], open_id, nickname, avatar_url, ts, row["id"]),
            )
            user_id = row["id"]
        else:
            user_id = random_token("usr")
            self.db.execute(
                "INSERT INTO users(id, wechat_union_id, wechat_open_id, nickname, avatar_url, created_at, last_login_at) VALUES(?,?,?,?,?,?,?)",
                (user_id, union_id or None, open_id, nickname, avatar_url, ts, ts),
            )

        identity_id = sha256_text(f"wechat:{open_id}")
        raw = json.dumps(userinfo, ensure_ascii=False, sort_keys=True)
        existing_identity = self.db.query_one("SELECT id FROM wechat_identities WHERE id=?", (identity_id,))
        if existing_identity:
            self.db.execute(
                """
                UPDATE wechat_identities
                SET user_id=?, union_id=?, raw_json=?, updated_at=?
                WHERE id=?
                """,
                (user_id, union_id or None, raw, ts, identity_id),
            )
        else:
            self.db.execute(
                """
                INSERT INTO wechat_identities(id, user_id, union_id, open_id, raw_json, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (identity_id, user_id, union_id or None, open_id, raw, ts, ts),
            )
        user = self.db.query_one("SELECT * FROM users WHERE id=?", (user_id,))
        return dict(user)

    def poll_wechat_login(self, query):
        nonce = query.get("loginNonce") or query.get("login_nonce") or ""
        if not nonce:
            raise HttpError(400, "missing loginNonce")

        row = self.db.query_one("SELECT * FROM desktop_login_nonces WHERE nonce=?", (nonce,))
        if not row:
            raise HttpError(404, "login not found")
        if row["expires_at"] < now() and row["status"] == "pending":
            self.db.execute("UPDATE desktop_login_nonces SET status='expired' WHERE nonce=?", (nonce,))
            return {"status": "expired"}
        if row["status"] != "completed":
            return {"status": row["status"], "expiresAt": row["expires_at"]}

        session = self.create_desktop_session(row["user_id"], row["device_id"])
        self.db.execute("UPDATE desktop_login_nonces SET status='consumed' WHERE nonce=?", (nonce,))
        return {"status": "completed", **session}

    def create_desktop_session(self, user_id, device_id=""):
        token = random_token("ds")
        session_id = random_token("sess")
        created_at = now()
        expires_at = created_at + self.settings.session_ttl_seconds
        self.db.execute(
            "INSERT INTO desktop_sessions(id, user_id, token_hash, device_id, created_at, expires_at) VALUES(?,?,?,?,?,?)",
            (session_id, user_id, sha256_text(token), device_id, created_at, expires_at),
        )
        self.db.audit("desktop_session_created", actor_user_id=user_id, device_id=device_id)
        return {
            "desktopSession": token,
            "sessionId": session_id,
            "expiresAt": expires_at,
            "user": self.public_user(self.db.query_one("SELECT * FROM users WHERE id=?", (user_id,))),
            "tenants": self.tenants_for_user(user_id),
        }

    def require_session(self, headers):
        auth = headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            raise HttpError(401, "missing bearer token")
        token_hash = sha256_text(auth[len("Bearer ") :].strip())
        row = self.db.query_one(
            """
            SELECT users.* FROM desktop_sessions
            JOIN users ON users.id = desktop_sessions.user_id
            WHERE desktop_sessions.token_hash=? AND desktop_sessions.revoked_at IS NULL AND desktop_sessions.expires_at>=?
            """,
            (token_hash, now()),
        )
        if not row or row["status"] != "active":
            raise HttpError(401, "invalid session")
        return dict(row)

    def require_admin(self, headers):
        token = headers.get("x-admin-token", "")
        if not self.settings.admin_token or token != self.settings.admin_token:
            raise HttpError(403, "admin token required")

    def public_user(self, user):
        row = dict(user)
        return {
            "id": row["id"],
            "nickname": row["nickname"],
            "avatarUrl": row["avatar_url"],
            "status": row["status"],
        }

    def tenants_for_user(self, user_id):
        rows = self.db.query_all(
            """
            SELECT tenants.*, tenant_memberships.role AS member_role
            FROM tenant_memberships
            JOIN tenants ON tenants.id = tenant_memberships.tenant_id
            WHERE tenant_memberships.user_id=?
              AND tenant_memberships.status='active'
              AND tenants.status='active'
            ORDER BY tenants.display_name
            """,
            (user_id,),
        )
        return [row_to_tenant(row, row["member_role"]) for row in rows]

    def public_workspaces(self):
        rows = self.db.query_all(
            """
            SELECT * FROM tenants
            WHERE status='active'
            ORDER BY display_name
            """
        )
        return {
            "version": 1,
            "workspaces": [
                {
                    "id": row["id"],
                    "profile": row["profile"],
                    "displayName": row["display_name"],
                    "gatewayUrl": row["gateway_url"],
                    "authMode": row["auth_mode"] or "none",
                }
                for row in rows
            ],
        }

    def gateway_ticket(self, user, tenant_id):
        row = self.db.query_one(
            """
            SELECT tenants.*, tenant_memberships.role AS member_role
            FROM tenant_memberships
            JOIN tenants ON tenants.id = tenant_memberships.tenant_id
            WHERE tenant_memberships.user_id=? AND tenants.id=?
              AND tenant_memberships.status='active'
              AND tenants.status='active'
            """,
            (user["id"], tenant_id),
        )
        if not row:
            raise HttpError(403, "tenant access denied")

        exp = now() + self.settings.gateway_ticket_ttl_seconds
        ticket = sign_json(
            {
                "typ": "creator_gateway_ticket",
                "sub": user["id"],
                "tenant": row["id"],
                "profile": row["profile"],
                "role": row["member_role"],
                "iat": now(),
                "exp": exp,
            },
            self.settings.secret,
        )
        self.db.audit("gateway_ticket_issued", actor_user_id=user["id"], tenant_id=row["id"], role=row["member_role"])
        return {
            "tenant": row_to_tenant(row, row["member_role"]),
            "gatewayTicket": ticket,
            "expiresAt": exp,
        }

    def dev_login(self, data):
        open_id = str(data.get("openId") or "dev-openid")
        union_id = str(data.get("unionId") or "dev-unionid")
        user = self.upsert_wechat_user(
            open_id=open_id,
            union_id=union_id,
            userinfo={"openid": open_id, "unionid": union_id, "nickname": data.get("nickname") or "Dev User"},
        )
        return self.create_desktop_session(user["id"], str(data.get("deviceId") or "dev"))

    def handle_admin(self, method, route, data):
        if method == "POST" and route == "/admin/tenants":
            return self.json(self.admin_upsert_tenant(data), 201)

        tenant_match = re.match(r"^/admin/tenants/([^/]+)$", route)
        if method == "PUT" and tenant_match:
            data["id"] = tenant_match.group(1)
            return self.json(self.admin_upsert_tenant(data))

        if method == "POST" and route == "/admin/users":
            return self.json(self.admin_create_user(data), 201)

        member_match = re.match(r"^/admin/tenants/([^/]+)/members/([^/]+)$", route)
        if method == "PUT" and member_match:
            return self.json(self.admin_set_membership(member_match.group(1), member_match.group(2), data))

        if method == "GET" and route == "/admin/tenants":
            rows = self.db.query_all("SELECT * FROM tenants ORDER BY id")
            return self.json({"tenants": [row_to_tenant(row) for row in rows]})

        if method == "GET" and route == "/admin/audit-events":
            rows = self.db.query_all("SELECT * FROM audit_events ORDER BY id DESC LIMIT 200")
            return self.json({"events": [dict(row) for row in rows]})

        raise HttpError(404, "admin route not found")

    def admin_upsert_tenant(self, data):
        tenant_id = str(data.get("id") or "")
        if not TENANT_ID_RE.match(tenant_id):
            raise HttpError(400, "invalid tenant id")
        profile = str(data.get("profile") or "")
        display_name = str(data.get("displayName") or data.get("display_name") or tenant_id)
        gateway_url = str(data.get("gatewayUrl") or data.get("gateway_url") or "")
        if not profile or not gateway_url.startswith(("http://", "https://")):
            raise HttpError(400, "profile and gatewayUrl are required")
        features = data.get("features") or {}
        if not isinstance(features, dict):
            raise HttpError(400, "features must be an object")
        ts = now()
        existing = self.db.query_one("SELECT id FROM tenants WHERE id=?", (tenant_id,))
        if existing:
            self.db.execute(
                "UPDATE tenants SET profile=?, display_name=?, gateway_url=?, auth_mode=?, features_json=?, status=?, updated_at=? WHERE id=?",
                (
                    profile,
                    display_name,
                    gateway_url,
                    str(data.get("authMode") or data.get("auth_mode") or "ticket"),
                    json.dumps(features, ensure_ascii=False, sort_keys=True),
                    str(data.get("status") or "active"),
                    ts,
                    tenant_id,
                ),
            )
        else:
            self.db.execute(
                "INSERT INTO tenants(id, profile, display_name, gateway_url, auth_mode, features_json, status, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    tenant_id,
                    profile,
                    display_name,
                    gateway_url,
                    str(data.get("authMode") or data.get("auth_mode") or "ticket"),
                    json.dumps(features, ensure_ascii=False, sort_keys=True),
                    str(data.get("status") or "active"),
                    ts,
                    ts,
                ),
            )
        self.db.audit("admin_tenant_upserted", tenant_id=tenant_id)
        return row_to_tenant(self.db.query_one("SELECT * FROM tenants WHERE id=?", (tenant_id,)))

    def admin_create_user(self, data):
        open_id = str(data.get("wechatOpenId") or data.get("wechat_open_id") or "")
        union_id = str(data.get("wechatUnionId") or data.get("wechat_union_id") or "")
        if not open_id and not union_id:
            raise HttpError(400, "wechatOpenId or wechatUnionId is required")
        user = self.upsert_wechat_user(
            open_id=open_id or f"manual-{union_id}",
            union_id=union_id,
            userinfo={
                "openid": open_id,
                "unionid": union_id,
                "nickname": data.get("nickname") or "",
                "headimgurl": data.get("avatarUrl") or data.get("avatar_url") or "",
            },
        )
        self.db.audit("admin_user_created", actor_user_id=user["id"])
        return self.public_user(user)

    def admin_set_membership(self, tenant_id, user_id, data):
        role = str(data.get("role") or "viewer")
        if role not in ROLE_VALUES:
            raise HttpError(400, "invalid role")
        if not self.db.query_one("SELECT id FROM users WHERE id=?", (user_id,)):
            raise HttpError(404, "user not found")
        if not self.db.query_one("SELECT id FROM tenants WHERE id=?", (tenant_id,)):
            raise HttpError(404, "tenant not found")
        ts = now()
        status = str(data.get("status") or "active")
        existing = self.db.query_one(
            "SELECT user_id FROM tenant_memberships WHERE user_id=? AND tenant_id=?",
            (user_id, tenant_id),
        )
        if existing:
            self.db.execute(
                "UPDATE tenant_memberships SET role=?, status=?, updated_at=? WHERE user_id=? AND tenant_id=?",
                (role, status, ts, user_id, tenant_id),
            )
        else:
            self.db.execute(
                """
                INSERT INTO tenant_memberships(user_id, tenant_id, role, status, created_by, created_at, updated_at)
                VALUES(?,?,?,?,?,?,?)
                """,
                (user_id, tenant_id, role, status, str(data.get("createdBy") or ""), ts, ts),
            )
        self.db.audit("admin_membership_set", actor_user_id=user_id, tenant_id=tenant_id, role=role)
        return {"ok": True, "userId": user_id, "tenantId": tenant_id, "role": role}
