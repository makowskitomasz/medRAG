import jwt
import pytest

from app.connectors.jwt_connector import create_token, decode_token, hash_password, verify_password


def test_password_round_trip():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_token_round_trip():
    token = create_token("user-id-123", "user")
    payload = decode_token(token)
    assert payload["sub"] == "user-id-123"
    assert payload["role"] == "user"


def test_token_invalid_raises():
    with pytest.raises(jwt.InvalidTokenError):
        decode_token("not.a.valid.token")


def test_expired_token_raises():
    from datetime import UTC, datetime, timedelta

    import jwt as _jwt

    from app.config import settings

    expired_payload = {
        "sub": "user-id",
        "role": "user",
        "exp": datetime.now(UTC) - timedelta(seconds=1),
    }
    expired_token = _jwt.encode(
        expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired_token)
