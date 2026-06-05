from fastapi.security import HTTPAuthorizationCredentials

from app.api.dependencies import _has_valid_bearer_token
from app.core.config import settings


def test_bearer_token_auth_is_false_when_token_is_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_token", None)

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="secret-token",
    )

    assert not _has_valid_bearer_token(credentials)


def test_bearer_token_auth_accepts_matching_bearer_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_token", "secret-token")

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="secret-token",
    )

    assert _has_valid_bearer_token(credentials)


def test_bearer_token_auth_rejects_missing_token(monkeypatch) -> None:
    monkeypatch.setattr(settings, "api_token", "secret-token")

    assert not _has_valid_bearer_token(None)
