# src/api/routes/saved_teams.py
"""Saved teams API routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..models.saved_team import (
    SaveTeamRequest,
    UpdateMemberRequest,
    UpdateTeamRequest,
    SavedTeamDetail,
    SavedTeamSummary,
)
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
def save_team_endpoint(body: SaveTeamRequest):
    """Save a team with its score, breakdown, and analysis snapshot.

    Args:
        body: Team name, 6 members, score, breakdown, and analysis.

    Returns:
        The newly created SavedTeamDetail.
    """
    with get_db_connection() as conn:
        return save_team(conn, body.name, body.members, body.score, body.breakdown, body.analysis)


@router.get("/", response_model=list[SavedTeamSummary])
def list_teams_endpoint():
    """List all saved teams (no analysis detail), newest first.

    Returns:
        List of SavedTeamSummary.
    """
    with get_db_connection() as conn:
        return list_teams(conn)


@router.get("/{team_id}", response_model=SavedTeamDetail)
def get_team_endpoint(team_id: int):
    """Fetch a single saved team with full analysis.

    Args:
        team_id: Primary key of the saved team.

    Returns:
        SavedTeamDetail.
    """
    try:
        with get_db_connection() as conn:
            return get_team(conn, team_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{team_id}", response_model=SavedTeamDetail)
def update_team_endpoint(team_id: int, body: UpdateTeamRequest):
    """Update team name and/or snapshot fields.

    Args:
        team_id: Primary key of the saved team.
        body: Fields to update — at least one must be non-null.

    Returns:
        Updated SavedTeamDetail.
    """
    if not body.has_update():
        raise HTTPException(status_code=422, detail="At least one field must be provided")
    try:
        with get_db_connection() as conn:
            return update_team(
                conn, team_id,
                name=body.name,
                score=body.score,
                breakdown=body.breakdown,
                analysis=body.analysis,
            )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{team_id}/members/{slot}", response_model=SavedTeamDetail)
def update_member_endpoint(team_id: int, slot: int, body: UpdateMemberRequest):
    """Patch a single member slot's fields without re-scoring the team.

    Args:
        team_id: Primary key of the saved team.
        slot: Member index 0–5.
        body: Fields to update — pokemon_name and set_id are required;
              item, tera_type, evs, moves, nature, and ability are optional.

    Returns:
        Updated SavedTeamDetail.
    """
    if not 0 <= slot <= 5:
        raise HTTPException(status_code=422, detail="slot must be between 0 and 5")
    try:
        with get_db_connection() as conn:
            return update_member(conn, team_id, slot, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{team_id}", status_code=204)
def delete_team_endpoint(team_id: int):
    """Delete a saved team and its members.

    Args:
        team_id: Primary key of the saved team.
    """
    try:
        with get_db_connection() as conn:
            delete_team(conn, team_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(status_code=204)
