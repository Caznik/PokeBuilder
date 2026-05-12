# src/api/routes/battle_logs.py
"""Battle logs API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from ..models.auth import UserOut
from ..models.battle_log import BattleLogCreate, BattleLogOut
from ..services.auth_service import get_current_user
from ..services.battle_log_service import create_log, delete_log, get_log, list_logs
from ..db import get_db_connection

router = APIRouter(prefix="/battle-logs", tags=["battle-logs"])


@router.post("/", response_model=BattleLogOut, status_code=201)
def create_log_endpoint(body: BattleLogCreate, user: UserOut = Depends(get_current_user)):
    """Create a new battle log entry for the authenticated user.

    Args:
        body: Validated BattleLogCreate payload.
        user: Authenticated user from access_token cookie.

    Returns:
        The newly created BattleLogOut.
    """
    with get_db_connection() as conn:
        return create_log(conn, user.id, body)


@router.get("/", response_model=list[BattleLogOut])
def list_logs_endpoint(
    user: UserOut = Depends(get_current_user),
    regulation_id: int | None = Query(default=None, description="Filter by regulation FK"),
    format: str | None = Query(default=None, description="Filter by format: singles or vgc"),
    result: str | None = Query(default=None, description="Filter by result: win, loss, or tie"),
):
    """List battle logs for the authenticated user, newest first.

    Args:
        user: Authenticated user from access_token cookie.
        regulation_id: Optional regulation FK filter.
        format: Optional format filter.
        result: Optional result filter.

    Returns:
        List of BattleLogOut, newest first.
    """
    with get_db_connection() as conn:
        return list_logs(conn, user.id, regulation_id=regulation_id, format=format, result=result)


@router.get("/{log_id}", response_model=BattleLogOut)
def get_log_endpoint(log_id: int, user: UserOut = Depends(get_current_user)):
    """Fetch a single battle log for the authenticated user.

    Args:
        log_id: Primary key of the battle log.
        user: Authenticated user from access_token cookie.

    Returns:
        BattleLogOut for the requested log.
    """
    try:
        with get_db_connection() as conn:
            return get_log(conn, log_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{log_id}", status_code=204)
def delete_log_endpoint(log_id: int, user: UserOut = Depends(get_current_user)):
    """Delete a battle log owned by the authenticated user.

    Args:
        log_id: Primary key of the battle log.
        user: Authenticated user from access_token cookie.
    """
    try:
        with get_db_connection() as conn:
            delete_log(conn, log_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(status_code=204)
