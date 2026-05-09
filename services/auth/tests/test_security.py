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
