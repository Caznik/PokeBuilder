"""Authentication service: password hashing, JWT, refresh token DB ops, OAuth client."""
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request, Response, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..models.auth import UserOut

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8000/auth/google/callback",
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return bcrypt hash of plain-text password."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches hashed bcrypt password."""
    return _pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, email: str) -> str:
    """Create a signed JWT access token valid for ACCESS_TOKEN_EXPIRE_MINUTES."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "email": email, "exp": expire, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token. Raises 401 on any failure."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise JWTError("not an access token")
        return payload
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


def create_refresh_token() -> str:
    """Return a cryptographically random 64-char hex string."""
    return secrets.token_hex(32)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def store_refresh_token(conn: Any, user_id: int, raw_token: str) -> None:
    """Insert a hashed refresh token into the DB.

    Args:
        conn: Active psycopg2 connection.
        user_id: Owner's user id.
        raw_token: The raw (unhashed) refresh token string.
    """
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
            (user_id, _hash_token(raw_token), expires_at),
        )
    conn.commit()


def validate_and_rotate_refresh_token(conn: Any, raw_token: str) -> tuple[int, str]:
    """Delete old refresh token and insert a new one. Returns (user_id, new_raw_token).

    Args:
        conn: Active psycopg2 connection.
        raw_token: The raw (unhashed) refresh token to validate and rotate.

    Returns:
        Tuple of (user_id, new_raw_token).

    Raises:
        HTTPException: 401 if token not found or expired.
    """
    token_hash = _hash_token(raw_token)
    new_raw_token = create_refresh_token()
    new_expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM refresh_tokens WHERE token_hash = %s AND expires_at > now() RETURNING user_id",
            (token_hash,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
        user_id = row[0]
        cur.execute(
            "INSERT INTO refresh_tokens (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
            (user_id, _hash_token(new_raw_token), new_expires_at),
        )
    conn.commit()
    return user_id, new_raw_token


def revoke_refresh_token(conn: Any, raw_token: str) -> None:
    """Delete a refresh token from the DB (logout).

    Args:
        conn: Active psycopg2 connection.
        raw_token: The raw (unhashed) refresh token to revoke.
    """
    with conn.cursor() as cur:
        cur.execute("DELETE FROM refresh_tokens WHERE token_hash = %s", (_hash_token(raw_token),))
    conn.commit()


def get_current_user(request: Request, response: Response) -> UserOut:
    """FastAPI dependency: validate access_token cookie, slide its expiry, and return the current user.

    Args:
        request: The incoming FastAPI request (used to read cookies).
        response: Used to re-issue a fresh access_token cookie on every request.

    Returns:
        UserOut with id and email extracted from the JWT.

    Raises:
        HTTPException: 401 if cookie is missing or token is invalid.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_access_token(token)
    user = UserOut(id=int(payload["sub"]), email=payload["email"])
    new_token = create_access_token(user.id, user.email)
    response.set_cookie(
        "access_token", new_token,
        httponly=True, samesite="lax", max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return user
