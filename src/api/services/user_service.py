"""DB operations for the users table."""
from typing import Any

from ..models.auth import UserOut


def create_user(conn: Any, email: str, hashed_password: str) -> UserOut:
    """Insert a new user. Raises ValueError if email already registered.

    Args:
        conn: Active psycopg2 connection.
        email: User email address.
        hashed_password: Bcrypt-hashed password string.

    Returns:
        UserOut with the new user's id and email.

    Raises:
        ValueError: If the email is already registered.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone() is not None:
            raise ValueError("Email already registered")
        cur.execute(
            "INSERT INTO users (email, hashed_password) VALUES (%s, %s) RETURNING id, email",
            (email, hashed_password),
        )
        row = cur.fetchone()
    conn.commit()
    return UserOut(id=row[0], email=row[1])


def get_user_by_email(conn: Any, email: str) -> tuple | None:
    """Fetch (id, email, hashed_password) for the given email, or None.

    Args:
        conn: Active psycopg2 connection.
        email: Email address to look up.

    Returns:
        Row tuple (id, email, hashed_password) or None if not found.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, hashed_password FROM users WHERE email = %s", (email,)
        )
        return cur.fetchone()


def get_user_by_id(conn: Any, user_id: int) -> tuple | None:
    """Fetch (id, email) for the given user_id, or None.

    Args:
        conn: Active psycopg2 connection.
        user_id: Primary key of the user.

    Returns:
        Row tuple (id, email) or None if not found.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id, email FROM users WHERE id = %s", (user_id,))
        return cur.fetchone()


def get_or_create_google_user(conn: Any, email: str, google_id: str) -> UserOut:
    """Find a user by Google ID, auto-link by email, or create a new OAuth-only user.

    Resolution order:
    1. Look up by google_id -> return user if found.
    2. Look up by email -> if found, update google_id (auto-link) and return user.
    3. Otherwise insert a new user with hashed_password = NULL.

    Args:
        conn: Active psycopg2 connection.
        email: Email address from Google userinfo.
        google_id: Google 'sub' claim (stable unique identifier).

    Returns:
        UserOut for the resolved or newly created user.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT id, email FROM users WHERE google_id = %s", (google_id,))
        row = cur.fetchone()
        if row:
            return UserOut(id=row[0], email=row[1])

        cur.execute("SELECT id, email FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE users SET google_id = %s WHERE id = %s",
                (google_id, row[0]),
            )
            conn.commit()
            return UserOut(id=row[0], email=row[1])

        cur.execute(
            "INSERT INTO users (email, google_id) VALUES (%s, %s) RETURNING id, email",
            (email, google_id),
        )
        row = cur.fetchone()
    conn.commit()
    return UserOut(id=row[0], email=row[1])
