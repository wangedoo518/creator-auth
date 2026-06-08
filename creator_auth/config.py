import os
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.environ.get(name)
    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        return default


class Settings:
    def __init__(
        self,
        host,
        port,
        public_base_url,
        db_path,
        secret,
        admin_token,
        wechat_app_id,
        wechat_app_secret,
        wechat_redirect_uri,
        login_ttl_seconds,
        session_ttl_seconds,
        gateway_ticket_ttl_seconds,
        allow_dev_login,
    ):
        self.host = host
        self.port = port
        self.public_base_url = public_base_url
        self.db_path = db_path
        self.secret = secret
        self.admin_token = admin_token
        self.wechat_app_id = wechat_app_id
        self.wechat_app_secret = wechat_app_secret
        self.wechat_redirect_uri = wechat_redirect_uri
        self.login_ttl_seconds = login_ttl_seconds
        self.session_ttl_seconds = session_ttl_seconds
        self.gateway_ticket_ttl_seconds = gateway_ticket_ttl_seconds
        self.allow_dev_login = allow_dev_login


def load_settings() -> Settings:
    _load_dotenv()

    return Settings(
        host=os.environ.get("CREATOR_AUTH_HOST", "127.0.0.1"),
        port=_int_env("CREATOR_AUTH_PORT", 8088),
        public_base_url=os.environ.get("CREATOR_AUTH_PUBLIC_BASE_URL", "http://127.0.0.1:8088").rstrip("/"),
        db_path=os.environ.get("CREATOR_AUTH_DB", "creator-auth.db"),
        secret=os.environ.get("CREATOR_AUTH_SECRET", ""),
        admin_token=os.environ.get("CREATOR_AUTH_ADMIN_TOKEN", ""),
        wechat_app_id=os.environ.get("WECHAT_APP_ID", ""),
        wechat_app_secret=os.environ.get("WECHAT_APP_SECRET", ""),
        wechat_redirect_uri=os.environ.get("WECHAT_REDIRECT_URI", ""),
        login_ttl_seconds=_int_env("CREATOR_AUTH_LOGIN_TTL_SECONDS", 300),
        session_ttl_seconds=_int_env("CREATOR_AUTH_SESSION_TTL_SECONDS", 2_592_000),
        gateway_ticket_ttl_seconds=_int_env("CREATOR_AUTH_GATEWAY_TICKET_TTL_SECONDS", 300),
        allow_dev_login=_bool_env("CREATOR_AUTH_ALLOW_DEV_LOGIN", False),
    )
