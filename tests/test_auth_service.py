"""Unit tests for auth_service — no DB required."""
import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    create_refresh_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from src.api.models.auth import UserOut


# --- Password hashing ---

def test_hash_password_returns_bcrypt_hash():
    hashed = hash_password("mypassword")
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("mypassword")
    assert verify_password("wrongpassword", hashed) is False


# --- JWT access token ---

def test_create_access_token_is_decodable():
    token = create_access_token(user_id=42, email="u@example.com")
    payload = decode_access_token(token)
    assert payload["sub"] == "42"
    assert payload["email"] == "u@example.com"
    assert payload["type"] == "access"


def test_decode_access_token_expired_raises_401():
    with patch("src.api.services.auth_service.ACCESS_TOKEN_EXPIRE_MINUTES", -1):
        token = create_access_token(user_id=1, email="u@example.com")
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401


def test_decode_access_token_invalid_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("not.a.valid.jwt")
    assert exc_info.value.status_code == 401


def test_decode_access_token_wrong_type_raises_401():
    from jose import jwt as jose_jwt
    from src.api.services.auth_service import SECRET_KEY, ALGORITHM
    from datetime import datetime, timedelta, timezone
    payload = {
        "sub": "1", "email": "u@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "type": "refresh",
    }
    token = jose_jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401


# --- Refresh token ---

def test_create_refresh_token_is_64_char_hex():
    token = create_refresh_token()
    assert len(token) == 64
    int(token, 16)  # raises if not hex


# --- get_current_user dependency ---

def test_get_current_user_valid_cookie():
    access_token = create_access_token(user_id=7, email="test@example.com")
    request = MagicMock()
    request.cookies = {"access_token": access_token}
    response = MagicMock()
    user = get_current_user(request, response)
    assert user.id == 7
    assert user.email == "test@example.com"


def test_get_current_user_no_cookie_raises_401():
    request = MagicMock()
    request.cookies = {}
    response = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(request, response)
    assert exc_info.value.status_code == 401


def test_get_current_user_invalid_token_raises_401():
    request = MagicMock()
    request.cookies = {"access_token": "garbage"}
    response = MagicMock()
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(request, response)
    assert exc_info.value.status_code == 401


def test_get_current_user_slides_access_token_expiry():
    access_token = create_access_token(user_id=7, email="test@example.com")
    request = MagicMock()
    request.cookies = {"access_token": access_token}
    response = MagicMock()
    get_current_user(request, response)
    response.set_cookie.assert_called_once()
    args, kwargs = response.set_cookie.call_args
    assert args[0] == "access_token"
    new_token = args[1]
    payload = decode_access_token(new_token)
    assert payload["sub"] == "7"
    assert payload["email"] == "test@example.com"
    assert kwargs.get("httponly") is True
    assert kwargs.get("max_age") == ACCESS_TOKEN_EXPIRE_MINUTES * 60
