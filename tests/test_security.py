from app.core.security import create_auth_token, hash_password, parse_auth_token, verify_password


def test_password_hash_verification() -> None:
    password_hash = hash_password("secret")

    assert password_hash != "secret"
    assert verify_password("secret", password_hash)
    assert not verify_password("wrong", password_hash)


def test_auth_token_round_trip() -> None:
    token = create_auth_token(12, "admin")

    payload = parse_auth_token(token)

    assert payload is not None
    assert payload["sub"] == "12"
    assert payload["username"] == "admin"
    assert isinstance(payload["exp"], int)


def test_tampered_auth_token_is_rejected() -> None:
    token = create_auth_token(12, "admin")

    assert parse_auth_token(token + "x") is None
