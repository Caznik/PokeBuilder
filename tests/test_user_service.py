"""Unit tests for user_service."""
import pytest
from unittest.mock import MagicMock

from src.api.services.user_service import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_or_create_google_user,
)
from src.api.models.auth import UserOut


def _make_conn(fetchone_returns=None):
    conn = MagicMock()
    cur = MagicMock()
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    if fetchone_returns is not None:
        cur.fetchone.side_effect = fetchone_returns
    conn.cursor.return_value = cur
    return conn


def test_create_user_returns_user_out():
    conn = _make_conn(fetchone_returns=[None, (42, "u@example.com")])
    user = create_user(conn, "u@example.com", "hashed_pw")
    assert isinstance(user, UserOut)
    assert user.id == 42
    assert user.email == "u@example.com"
    conn.commit.assert_called_once()


def test_create_user_duplicate_raises_value_error():
    conn = _make_conn(fetchone_returns=[(1,)])  # existing user found
    with pytest.raises(ValueError, match="already registered"):
        create_user(conn, "u@example.com", "hashed_pw")


def test_get_user_by_email_found():
    conn = _make_conn(fetchone_returns=[(1, "u@example.com", "hashed")])
    row = get_user_by_email(conn, "u@example.com")
    assert row == (1, "u@example.com", "hashed")


def test_get_user_by_email_not_found():
    conn = _make_conn(fetchone_returns=[None])
    row = get_user_by_email(conn, "missing@example.com")
    assert row is None


def test_get_user_by_id_found():
    conn = _make_conn(fetchone_returns=[(5, "u@example.com")])
    row = get_user_by_id(conn, 5)
    assert row == (5, "u@example.com")


def test_get_user_by_id_not_found():
    conn = _make_conn(fetchone_returns=[None])
    row = get_user_by_id(conn, 999)
    assert row is None


# --- get_or_create_google_user ---

def test_get_or_create_google_user_found_by_google_id():
    conn = _make_conn(fetchone_returns=[(3, "g@example.com")])
    user = get_or_create_google_user(conn, "g@example.com", "gid-123")
    assert user.id == 3
    assert user.email == "g@example.com"
    conn.commit.assert_not_called()


def test_get_or_create_google_user_auto_links_by_email():
    # First fetchone (google_id lookup) -> not found
    # Second fetchone (email lookup) -> existing password-only account
    conn = _make_conn(fetchone_returns=[None, (5, "existing@example.com")])
    user = get_or_create_google_user(conn, "existing@example.com", "gid-456")
    assert user.id == 5
    assert user.email == "existing@example.com"
    conn.commit.assert_called_once()


def test_get_or_create_google_user_creates_new():
    # First fetchone (google_id lookup) -> not found
    # Second fetchone (email lookup) -> not found
    # Third fetchone (INSERT RETURNING) -> new row
    conn = _make_conn(fetchone_returns=[None, None, (99, "new@example.com")])
    user = get_or_create_google_user(conn, "new@example.com", "gid-789")
    assert user.id == 99
    assert user.email == "new@example.com"
    conn.commit.assert_called_once()
