# src/api/routes/team.py
"""Team analysis API route."""

from typing import Annotated
from fastapi import APIRouter, Body, HTTPException

from ..models.team import TeamMemberInput, TeamAnalysisResponse, CoverageResult
from ..services.team_loader import load_team
from ..services.team_analysis import analyze_team
from ..db import get_db_connection

router = APIRouter(prefix="/team", tags=["team"])


@router.post("/analyze", response_model=TeamAnalysisResponse)
def analyze_team_endpoint(
    members: Annotated[list[TeamMemberInput], Body()],
):
    """Analyze a competitive team of 6 Pokémon builds.

    Args:
        members: Exactly 6 entries, each with a pokemon_name and set_id.

    Returns:
        Full team analysis including role composition, validation issues,
        type weaknesses/resistances, and offensive coverage.
    """
    if len(members) != 6:
        raise HTTPException(
            status_code=422,
            detail=f"Team must have exactly 6 members, got {len(members)}",
        )

    raw = [{"pokemon_name": m.pokemon_name, "set_id": m.set_id} for m in members]
    try:
        with get_db_connection() as conn:
            builds = load_team(conn, raw)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    result = analyze_team(builds)

    return TeamAnalysisResponse(
        valid=result["valid"],
        issues=result["issues"],
        roles=result["roles"],
        weaknesses=result["weaknesses"],
        resistances=result["resistances"],
        coverage=CoverageResult(**result["coverage"]),
    )
