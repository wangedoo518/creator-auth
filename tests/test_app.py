import json
import tempfile
import unittest

from creator_auth.app import CreatorAuthApp, HttpError
from creator_auth.config import Settings
from creator_auth.crypto import verify_signed_json
from creator_auth.db import Database


def make_settings(db_path):
    return Settings(
        host="127.0.0.1",
        port=0,
        public_base_url="http://127.0.0.1:8088",
        db_path=db_path,
        secret="test-secret",
        admin_token="admin-token",
        wechat_app_id="wx-app",
        wechat_app_secret="wx-secret",
        wechat_redirect_uri="http://127.0.0.1:8088/auth/wechat/callback",
        login_ttl_seconds=300,
        session_ttl_seconds=3600,
        gateway_ticket_ttl_seconds=300,
        allow_dev_login=True,
    )


class CreatorAuthAppTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(f"{self.tmp.name}/test.db")
        self.settings = make_settings(f"{self.tmp.name}/test.db")
        self.app = CreatorAuthApp(self.settings, self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def request(self, method, path, headers=None, body=None):
        raw_body = json.dumps(body or {}).encode("utf-8") if body is not None else b""
        return self.app.handle(method, path, headers or {}, raw_body)

    def test_health(self):
        status, _, payload = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["service"], "creator-auth")

    def test_public_workspaces_do_not_require_login(self):
        admin_headers = {"x-admin-token": "admin-token"}
        self.request(
            "POST",
            "/admin/tenants",
            admin_headers,
            {
                "id": "lufei",
                "profile": "lufei-creator-profile",
                "displayName": "路飞设计沉思录",
                "gatewayUrl": "https://claudewiki.cn/hermes",
                "authMode": "token",
            },
        )

        status, _, payload = self.request("GET", "/workspaces")

        self.assertEqual(status, 200)
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["workspaces"][0]["id"], "lufei")
        self.assertEqual(payload["workspaces"][0]["profile"], "lufei-creator-profile")
        self.assertEqual(payload["workspaces"][0]["gatewayUrl"], "https://claudewiki.cn/hermes")
        self.assertEqual(payload["workspaces"][0]["authMode"], "token")

    def test_public_workspaces_default_to_token_auth(self):
        admin_headers = {"x-admin-token": "admin-token"}
        self.request(
            "POST",
            "/admin/tenants",
            admin_headers,
            {
                "id": "career-coach",
                "profile": "career-coach-copilot",
                "displayName": "求职咨询助手",
                "gatewayUrl": "https://claudewiki.cn/hermes",
            },
        )

        status, _, payload = self.request("GET", "/workspaces")

        self.assertEqual(status, 200)
        self.assertEqual(payload["workspaces"][0]["authMode"], "token")

    def test_admin_tenant_user_membership_and_desktop_session_flow(self):
        admin_headers = {"x-admin-token": "admin-token"}
        status, _, tenant = self.request(
            "POST",
            "/admin/tenants",
            admin_headers,
            {
                "id": "career-coach",
                "profile": "career-coach-copilot",
                "displayName": "求职咨询助手",
                "gatewayUrl": "https://claudewiki.cn/hermes",
                "features": {"chat": True, "settings": False},
            },
        )
        self.assertEqual(status, 201)
        self.assertEqual(tenant["id"], "career-coach")

        status, _, user = self.request(
            "POST",
            "/admin/users",
            admin_headers,
            {"wechatUnionId": "union-1", "wechatOpenId": "open-1", "nickname": "顾问"},
        )
        self.assertEqual(status, 201)
        self.assertEqual(user["nickname"], "顾问")

        status, _, membership = self.request(
            "PUT",
            f"/admin/tenants/career-coach/members/{user['id']}",
            admin_headers,
            {"role": "operator"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(membership["role"], "operator")

        status, _, login = self.request(
            "POST",
            "/dev/login",
            body={"unionId": "union-1", "openId": "open-1", "nickname": "顾问"},
        )
        self.assertEqual(status, 200)
        token = login["desktopSession"]

        status, _, tenants = self.request("GET", "/me/tenants", {"authorization": f"Bearer {token}"})
        self.assertEqual(status, 200)
        self.assertEqual(tenants["tenants"][0]["id"], "career-coach")
        self.assertEqual(tenants["tenants"][0]["role"], "operator")

        status, _, ticket = self.request(
            "POST",
            "/tenants/career-coach/gateway-ticket",
            {"authorization": f"Bearer {token}"},
            {},
        )
        self.assertEqual(status, 200)
        payload = verify_signed_json(ticket["gatewayTicket"], "test-secret")
        self.assertEqual(payload["tenant"], "career-coach")
        self.assertEqual(payload["profile"], "career-coach-copilot")
        self.assertEqual(payload["role"], "operator")

    def test_non_member_cannot_get_gateway_ticket(self):
        self.request(
            "POST",
            "/admin/tenants",
            {"x-admin-token": "admin-token"},
            {
                "id": "lufei",
                "profile": "lufei-creator-profile",
                "displayName": "路飞设计沉思录",
                "gatewayUrl": "https://claudewiki.cn/hermes",
            },
        )
        _, _, login = self.request("POST", "/dev/login", body={"unionId": "other", "openId": "other"})
        with self.assertRaises(HttpError) as ctx:
            self.request("POST", "/tenants/lufei/gateway-ticket", {"authorization": f"Bearer {login['desktopSession']}"}, {})
        self.assertEqual(ctx.exception.status, 403)


if __name__ == "__main__":
    unittest.main()
