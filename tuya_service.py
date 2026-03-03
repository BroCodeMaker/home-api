import hashlib
import hmac
import time
import requests
import os
from typing import Optional

TUYA_BASE_URL = "https://openapi.tuyaeu.com"  # EU region; change to tuyaus.com for US

_token_cache: dict = {"token": None, "expires_at": 0}


def _sign(client_id: str, client_secret: str, t: str, access_token: str = "", method: str = "GET", path: str = "", body: str = "") -> str:
    str_to_sign = client_id + access_token + t
    content_hash = hashlib.sha256(body.encode()).hexdigest()
    str_to_sign += "\n" + method.upper() + "\n" + content_hash + "\n\n" + path
    return hmac.new(client_secret.encode(), str_to_sign.encode(), hashlib.sha256).hexdigest().upper()


def _get_token() -> str:
    client_id = os.environ["TUYA_CLIENT_ID"]
    client_secret = os.environ["TUYA_CLIENT_SECRET"]

    now = time.time()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    t = str(int(now * 1000))
    sign = _sign(client_id, client_secret, t, path="/v1.0/token?grant_type=1")

    headers = {
        "client_id": client_id,
        "sign": sign,
        "t": t,
        "sign_method": "HMAC-SHA256",
    }
    resp = requests.get(f"{TUYA_BASE_URL}/v1.0/token?grant_type=1", headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Tuya token error: {data}")

    _token_cache["token"] = data["result"]["access_token"]
    _token_cache["expires_at"] = now + data["result"]["expire_time"]
    return _token_cache["token"]


def _tuya_request(method: str, path: str, body: dict = None) -> dict:
    client_id = os.environ["TUYA_CLIENT_ID"]
    client_secret = os.environ["TUYA_CLIENT_SECRET"]
    token = _get_token()

    t = str(int(time.time() * 1000))
    import json
    body_str = json.dumps(body) if body else ""
    sign = _sign(client_id, client_secret, t, access_token=token, method=method, path=path, body=body_str)

    headers = {
        "client_id": client_id,
        "access_token": token,
        "sign": sign,
        "t": t,
        "sign_method": "HMAC-SHA256",
        "Content-Type": "application/json",
    }

    url = TUYA_BASE_URL + path
    if method.upper() == "GET":
        resp = requests.get(url, headers=headers, timeout=10)
    elif method.upper() == "POST":
        resp = requests.post(url, headers=headers, data=body_str, timeout=10)
    else:
        raise ValueError(f"Unsupported method: {method}")

    resp.raise_for_status()
    return resp.json()


def control_device(device_id: str, power: Optional[bool], brightness: Optional[int]) -> dict:
    commands = []
    if power is not None:
        commands.append({"code": "switch_led", "value": power})
    if brightness is not None:
        # Tuya brightness: 10–1000
        tuya_brightness = max(10, min(1000, int(brightness * 10)))
        commands.append({"code": "bright_value_v2", "value": tuya_brightness})

    if not commands:
        raise ValueError("No commands specified")

    result = _tuya_request("POST", f"/v1.0/devices/{device_id}/commands", {"commands": commands})
    if not result.get("success"):
        raise RuntimeError(f"Tuya command failed: {result}")
    return result


def get_device_status(device_id: str) -> dict:
    result = _tuya_request("GET", f"/v1.0/devices/{device_id}/status")
    if not result.get("success"):
        raise RuntimeError(f"Tuya status failed: {result}")
    return result
