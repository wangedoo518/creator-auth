import base64
import hashlib
import hmac
import json
import secrets
import time


def random_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def sign_json(payload, secret):
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    encoded = _b64url(body)
    sig = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded}.{_b64url(sig)}"


def verify_signed_json(token, secret):
    try:
        encoded, sig = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("invalid token shape") from exc

    expected = hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest()
    actual = _b64url_decode(sig)
    if not hmac.compare_digest(expected, actual):
        raise ValueError("invalid token signature")

    payload = json.loads(_b64url_decode(encoded).decode("utf-8"))
    exp = payload.get("exp")
    if exp is not None and int(exp) < int(time.time()):
        raise ValueError("token expired")

    return payload
