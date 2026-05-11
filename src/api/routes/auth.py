"""Authentication routes: register, login, logout, refresh, me, Google OAuth."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse

from ..db import get_db_connection
from ..models.auth import LoginRequest, RegisterRequest, UserOut
from ..services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    FRONTEND_URL,
    GOOGLE_REDIRECT_URI,
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    oauth,
    revoke_refresh_token,
    store_refresh_token,
    validate_and_rotate_refresh_token,
    verify_password,
)
from ..services.user_service import (
    create_user,
    get_or_create_google_user,
    get_user_by_email,
    get_user_by_id,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_ACCESS_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60
_REFRESH_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        "access_token", access_token,
        httponly=True, samesite="lax", max_age=_ACCESS_MAX_AGE,
    )
    response.set_cookie(
        "refresh_token", refresh_token,
        httponly=True, samesite="lax", max_age=_REFRESH_MAX_AGE,
    )


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterRequest):
    """Create a new account and return JWT cookies.

    Args:
        body: Email and password.

    Returns:
        UserOut with id and email; sets access_token and refresh_token cookies.

    Raises:
        HTTPException: 409 if email already registered.
    """
    with get_db_connection() as conn:
        try:
            user = create_user(conn, body.email, hash_password(body.password))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
        raw_refresh = create_refresh_token()
        store_refresh_token(conn, user.id, raw_refresh)

    access_token = create_access_token(user.id, user.email)
    response = JSONResponse(content=user.model_dump(), status_code=201)
    _set_auth_cookies(response, access_token, raw_refresh)
    return response


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest):
    """Verify credentials and return JWT cookies.

    Args:
        body: Email and password.

    Returns:
        UserOut; sets access_token and refresh_token cookies.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    with get_db_connection() as conn:
        row = get_user_by_email(conn, body.email)
        if not row or not verify_password(body.password, row[2]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        user = UserOut(id=row[0], email=row[1])
        raw_refresh = create_refresh_token()
        store_refresh_token(conn, user.id, raw_refresh)

    access_token = create_access_token(user.id, user.email)
    response = JSONResponse(content=user.model_dump())
    _set_auth_cookies(response, access_token, raw_refresh)
    return response


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    user: UserOut = Depends(get_current_user),
):
    """Revoke the refresh token and clear auth cookies.

    Args:
        request: Used to read the refresh_token cookie.
        response: Used to delete cookies.
        user: Injected current user (requires valid access_token cookie).

    Returns:
        Confirmation message.
    """
    raw_refresh = request.cookies.get("refresh_token")
    if raw_refresh:
        with get_db_connection() as conn:
            revoke_refresh_token(conn, raw_refresh)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


@router.post("/refresh", response_model=UserOut)
def refresh(request: Request):
    """Rotate the refresh token and issue a new access token.

    Args:
        request: Used to read the refresh_token cookie.

    Returns:
        UserOut; sets new access_token and refresh_token cookies.

    Raises:
        HTTPException: 401 if refresh token is missing, invalid, or expired.
    """
    raw_refresh = request.cookies.get("refresh_token")
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token"
        )
    with get_db_connection() as conn:
        user_id, new_raw_refresh = validate_and_rotate_refresh_token(conn, raw_refresh)
        row = get_user_by_id(conn, user_id)

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    user = UserOut(id=row[0], email=row[1])
    new_access = create_access_token(user.id, user.email)
    response = JSONResponse(content=user.model_dump())
    _set_auth_cookies(response, new_access, new_raw_refresh)
    return response


@router.get("/me", response_model=UserOut)
def me(user: UserOut = Depends(get_current_user)):
    """Return the current authenticated user.

    Args:
        user: Injected from access_token cookie.

    Returns:
        UserOut.
    """
    return user


@router.get("/google")
async def google_login(request: Request):
    """Redirect the browser to Google's OAuth2 authorization page.

    Args:
        request: Used by authlib to store OAuth state in the session.

    Returns:
        Redirect response to Google.
    """
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)


@router.get("/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth2 callback: resolve user, issue cookies, redirect to app.

    Args:
        request: Contains the OAuth code and state from Google.

    Returns:
        Redirect to /teams on success, /login?error=oauth_failed on any failure.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
        userinfo = token["userinfo"]
        with get_db_connection() as conn:
            user = get_or_create_google_user(conn, userinfo["email"], userinfo["sub"])
            raw_refresh = create_refresh_token()
            store_refresh_token(conn, user.id, raw_refresh)
        access_token = create_access_token(user.id, user.email)
        response = RedirectResponse(url=f"{FRONTEND_URL}/teams")
        _set_auth_cookies(response, access_token, raw_refresh)
        return response
    except Exception:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=oauth_failed")
