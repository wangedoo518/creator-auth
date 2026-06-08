import json
import os
import sys
from urllib.request import Request, urlopen


DEFAULT_TENANTS = [
    {
        "id": "lufei",
        "profile": "lufei-creator-profile",
        "displayName": "路飞设计沉思录",
        "gatewayUrl": "https://lufei.example.com/hermes",
        "authMode": "ticket",
        "features": {
            "chat": True,
            "skills": True,
            "artifacts": True,
            "cron": True,
            "settings": False,
        },
    },
    {
        "id": "career-coach",
        "profile": "career-coach-copilot",
        "displayName": "求职咨询助手",
        "gatewayUrl": "https://career.example.com/hermes",
        "authMode": "ticket",
        "features": {
            "chat": True,
            "skills": True,
            "artifacts": True,
            "cron": False,
            "settings": False,
        },
    },
]


def post_json(base_url, admin_token, path, payload):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(
        f"{base_url.rstrip('/')}{path}",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Admin-Token": admin_token,
        },
    )
    with urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    base_url = os.environ.get("CREATOR_AUTH_BASE_URL", "http://127.0.0.1:8088")
    admin_token = os.environ.get("CREATOR_AUTH_ADMIN_TOKEN", "")
    if not admin_token:
        print("CREATOR_AUTH_ADMIN_TOKEN is required", file=sys.stderr)
        return 2

    tenant_file = os.environ.get("CREATOR_AUTH_TENANTS_JSON")
    if tenant_file:
        with open(tenant_file, "r", encoding="utf-8") as f:
            tenants = json.load(f)
    else:
        tenants = DEFAULT_TENANTS

    for tenant in tenants:
        result = post_json(base_url, admin_token, "/admin/tenants", tenant)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
