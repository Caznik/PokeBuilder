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
