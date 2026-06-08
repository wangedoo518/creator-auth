import json
from urllib.parse import urlencode
from urllib.request import urlopen


WECHAT_QRCONNECT_URL = "https://open.weixin.qq.com/connect/qrconnect"
WECHAT_ACCESS_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WECHAT_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"


def build_qrconnect_url(app_id, redirect_uri, state):
    params = {
        "appid": app_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "snsapi_login",
        "state": state,
    }
    return f"{WECHAT_QRCONNECT_URL}?{urlencode(params)}#wechat_redirect"


def _get_json(url):
    with urlopen(url, timeout=10) as resp:
        data = resp.read().decode("utf-8")
    payload = json.loads(data)
    if "errcode" in payload and int(payload.get("errcode") or 0) != 0:
        raise RuntimeError(f"WeChat API error {payload.get('errcode')}: {payload.get('errmsg')}")
    return payload


def exchange_code(app_id, app_secret, code):
    params = {
        "appid": app_id,
        "secret": app_secret,
        "code": code,
        "grant_type": "authorization_code",
    }
    return _get_json(f"{WECHAT_ACCESS_TOKEN_URL}?{urlencode(params)}")


def fetch_userinfo(access_token, open_id):
    params = {
        "access_token": access_token,
        "openid": open_id,
        "lang": "zh_CN",
    }
    return _get_json(f"{WECHAT_USERINFO_URL}?{urlencode(params)}")
