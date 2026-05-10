"""Integration tests for /auth/* endpoints."""
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models.auth import UserOut

client = TestClient(app, raise_server_exceptions=False)

_USER = UserOut(id=1, email="test@example.com")


@contextmanager
def _mock_db():
    yield MagicMock()


# --- /auth/register ---

def test_register_success():
    with patch("src.api.routes.auth.get_db_connection", _mock_db), \
         patch("src.api.routes.auth.hash_password", return_value="hashed"), \
         patch("src.api.routes.auth.create_user", return_value=_USER), \
         patch("src.api.routes.auth.create_refresh_token", return_value="raw-refresh"), \
         patch("src.api.routes.auth.store_refresh_token"), \
         patch("src.api.routes.auth.create_access_token", return_value="acc.tok.en"):
        response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
    assert response.json()["id"] == 1
    assert "access_token" in response.cookies
    assert "refresh_token" in response.cookies


def test_register_duplicate_email_returns_409():
    with patch("src.api.routes.auth.get_db_connection", _mock_db), \
         patch("src.api.routes.auth.hash_password", return_value="hashed"), \
         patch("src.api.routes.auth.create_user", side_effect=ValueError("Email already registered")), \
         patch("src.api.routes.auth.create_refresh_token", return_value="raw-refresh"), \
         patch("src.api.routes.auth.store_refresh_token"), \
         patch("src.api.routes.auth.create_access_token", return_value="acc.tok.en"):
        response = client.post(
            "/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
    assert response.status_code == 409


def test_register_invalid_email_returns_422():
    response = client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert response.status_code == 422


# --- /auth/login ---

def test_login_success():
    with patch("src.api.routes.auth.get_db_connection", _mock_db), \
         patch("src.api.routes.auth.get_user_by_email", return_value=(1, "test@example.com", "hashed")), \
         patch("src.api.routes.auth.verify_password", return_value=True), \
         patch("src.api.routes.auth.create_refresh_token", return_value="raw-refresh"), \
         patch("src.api.routes.auth.store_refresh_token"), \
         patch("src.api.routes.auth.create_access_token", return_value="acc.tok.en"):
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "password123"},
        )
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    assert "access_token" in response.cookies


def test_login_wrong_password_returns_401():
    with patch("src.api.routes.auth.get_db_connection", _mock_db), \
         patch("src.api.routes.auth.get_user_by_email", return_value=(1, "test@example.com", "hashed")), \
         patch("src.api.routes.auth.verify_password", return_value=False):
        response = client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrongpass"},
        )
    assert response.status_code == 401


def test_login_unknown_email_returns_401():
    with patch("src.api.routes.auth.get_db_connection", _mock_db), \
         patch("src.api.routes.auth.get_user_by_email", return_value=None):
        response = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "password123"},
        )
    assert response.status_code == 401


# --- /auth/logout ---

def test_logout_clears_cookies():
    from src.api.services.auth_service import get_current_user

    def override():
        return _USER

    app.dependency_overrides[get_current_user] = override
    try:
        with patch("src.api.routes.auth.get_db_connection", _mock_db), \
             patch("src.api.routes.auth.revoke_refresh_token"):
            response = client.post("/auth/logout", cookies={"refresh_token": "tok"})
        assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_logout_unauthenticated_returns_401():
    response = client.post("/auth/logout")
    assert response.status_code == 401


# --- /auth/refresh ---

def test_refresh_success():
    with patch("src.api.routes.auth.get_db_connection", _mock_db), \
         patch("src.api.routes.auth.validate_and_rotate_refresh_token", return_value=(1, "new-raw")), \
         patch("src.api.routes.auth.get_user_by_id", return_value=(1, "test@example.com")), \
         patch("src.api.routes.auth.create_access_token", return_value="new.acc.tok"):
        response = client.post("/auth/refresh", cookies={"refresh_token": "old-raw"})
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"
    assert "access_token" in response.cookies


def test_refresh_no_cookie_returns_401():
    fresh = TestClient(app, raise_server_exceptions=False)
    response = fresh.post("/auth/refresh")
    assert response.status_code == 401


# --- /auth/me ---

def test_me_authenticated():
    from src.api.services.auth_service import get_current_user

    def override():
        return _USER

    app.dependency_overrides[get_current_user] = override
    try:
        response = client.get("/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_me_unauthenticated_returns_401():
    response = client.get("/auth/me")
    assert response.status_code == 401
