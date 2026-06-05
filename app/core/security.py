import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from app.core.config import settings


PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_ITERATIONS,
    )
    return "$".join(
        [
            PASSWORD_ALGORITHM,
            str(PASSWORD_ITERATIONS),
            salt,
            _b64encode(digest),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_raw, salt, digest = password_hash.split("$", maxsplit=3)
        iterations = int(iterations_raw)
    except ValueError:
        return False

    if algorithm != PASSWORD_ALGORITHM:
        return False

    expected_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return hmac.compare_digest(_b64encode(expected_digest), digest)


def create_auth_token(user_id: int, username: str) -> str:
    issued_at = int(time.time())
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": issued_at,
        "exp": issued_at + settings.auth_cookie_max_age,
    }
    body = _b64encode_json(payload)
    signature = _sign(body)
    return f"{body}.{signature}"


def parse_auth_token(token: str | None) -> dict[str, Any] | None:
    if not token or "." not in token:
        return None

    body, signature = token.rsplit(".", maxsplit=1)
    if not hmac.compare_digest(_sign(body), signature):
        return None

    try:
        payload = _b64decode_json(body)
    except (ValueError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None
    if not isinstance(payload.get("sub"), str):
        return None
    if not isinstance(payload.get("username"), str):
        return None
    if not isinstance(payload.get("exp"), int):
        return None
    if payload["exp"] < int(time.time()):
        return None
    return payload


def _sign(value: str) -> str:
    digest = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _b64encode_json(value: dict[str, Any]) -> str:
    return _b64encode(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _b64decode_json(value: str) -> Any:
    return json.loads(_b64decode(value))
