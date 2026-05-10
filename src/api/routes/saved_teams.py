# src/api/routes/saved_teams.py
"""Saved teams API routes."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from ..models.auth import UserOut
from ..models.saved_team import (
    SaveTeamRequest,
    UpdateMemberRequest,
    UpdateTeamRequest,
    SavedTeamDetail,
    SavedTeamSummary,
)
from ..services.auth_service import get_current_user
from ..services.saved_team_service import (
    delete_team,
    get_team,
    list_teams,
    save_team,
    update_member,
    update_team,
)
from ..db import get_db_connection

router = APIRouter(prefix="/saved-teams", tags=["saved-teams"])


@router.post("/", response_model=SavedTeamDetail, status_code=201)
def save_team_endpoint(body: SaveTeamRequest, user: UserOut = Depends(get_current_user)):
    """Save a team with its score, breakdown, and analysis snapshot.

    Args:
        body: Team name, 6 members, score, breakdown, and analysis.
        user: Authenticated user from access_token cookie.

    Returns:
        The newly created SavedTeamDetail.
    """
    with get_db_connection() as conn:
        return save_team(conn, user.id, body.name, body.members, body.score, body.breakdown, body.analysis)


@router.get("/", response_model=list[SavedTeamSummary])
def list_teams_endpoint(user: UserOut = Depends(get_current_user)):
    """List all saved teams for the current user, newest first.

    Args:
        user: Authenticated user from access_token cookie.

    Returns:
        List of SavedTeamSummary.
    """
    with get_db_connection() as conn:
        return list_teams(conn, user.id)


@router.get("/{team_id}", response_model=SavedTeamDetail)
def get_team_endpoint(team_id: int, user: UserOut = Depends(get_current_user)):
    """Fetch a single saved team with full analysis.

    Args:
        team_id: Primary key of the saved team.
        user: Authenticated user from access_token cookie.

    Returns:
        SavedTeamDetail.
    """
    try:
        with get_db_connection() as conn:
            return get_team(conn, team_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{team_id}", response_model=SavedTeamDetail)
def update_team_endpoint(team_id: int, body: UpdateTeamRequest, user: UserOut = Depends(get_current_user)):
    """Update team name and/or snapshot fields.

    Args:
        team_id: Primary key of the saved team.
        body: Fields to update — at least one must be non-null.
        user: Authenticated user from access_token cookie.

    Returns:
        Updated SavedTeamDetail.
    """
    if not body.has_update():
        raise HTTPException(status_code=422, detail="At least one field must be provided")
    try:
        with get_db_connection() as conn:
            return update_team(
                conn, team_id, user.id,
                name=body.name,
                score=body.score,
                breakdown=body.breakdown,
                analysis=body.analysis,
            )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{team_id}/members/{slot}", response_model=SavedTeamDetail)
def update_member_endpoint(
    team_id: int,
    slot: int,
    body: UpdateMemberRequest,
    user: UserOut = Depends(get_current_user),
):
    """Patch a single member slot's fields without re-scoring the team.

    Args:
        team_id: Primary key of the saved team.
        slot: Member index 0–5.
        body: Fields to update.
        user: Authenticated user from access_token cookie.

    Returns:
        Updated SavedTeamDetail.
    """
    if not 0 <= slot <= 5:
        raise HTTPException(status_code=422, detail="slot must be between 0 and 5")
    try:
        with get_db_connection() as conn:
            return update_member(conn, team_id, user.id, slot, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{team_id}", status_code=204)
def delete_team_endpoint(team_id: int, user: UserOut = Depends(get_current_user)):
    """Delete a saved team and its members.

    Args:
        team_id: Primary key of the saved team.
        user: Authenticated user from access_token cookie.
    """
    try:
        with get_db_connection() as conn:
            delete_team(conn, team_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(status_code=204)
