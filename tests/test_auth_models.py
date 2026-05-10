"""Tests for auth Pydantic models."""
import pytest
from pydantic import ValidationError
from src.api.models.auth import RegisterRequest, LoginRequest, UserOut


def test_register_request_valid():
    r = RegisterRequest(email="user@example.com", password="password123")
    assert r.email == "user@example.com"


def test_register_request_invalid_email():
    with pytest.raises(ValidationError):
        RegisterRequest(email="not-an-email", password="password123")


def test_register_request_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="short")


def test_login_request_valid():
    r = LoginRequest(email="user@example.com", password="anypassword")
    assert r.email == "user@example.com"


def test_user_out_fields():
    u = UserOut(id=1, email="user@example.com")
    assert u.id == 1
    assert u.email == "user@example.com"
