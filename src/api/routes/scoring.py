# src/api/routes/scoring.py
"""Team scoring API route."""

from typing import Annotated

from fastapi import APIRouter, Body, HTTPException

from ..models.team import TeamMemberInput, TeamAnalysisResponse, CoverageResult
from ..models.scoring import ScoreResponse, ScoreBreakdown, ScoreComponent
from ..services.team_loader import load_team
from ..services.team_analysis import analyze_team
from ..services.team_scorer import score_team
from ..db import get_db_connection

router = APIRouter(prefix="/team", tags=["team"])


@router.post("/score", response_model=ScoreResponse)
def score_team_endpoint(
    members: Annotated[list[TeamMemberInput], Body()],
):
    """Score a competitive team of 6 Pokémon builds.

    Args:
        members: Exactly 6 entries, each with a pokemon_name and set_id.

    Returns:
        ScoreResponse with a 0–10 aggregate score, per-component breakdown
        (each with a numeric score and rationale string), and the full
        Sprint 6 analysis included for free.
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

    report = analyze_team(builds)
    scoring = score_team(report, builds)

    bd = scoring["breakdown"]
    breakdown = ScoreBreakdown(
        coverage=ScoreComponent(**bd["coverage"]),
        defensive=ScoreComponent(**bd["defensive"]),
        role=ScoreComponent(**bd["role"]),
        speed_control=ScoreComponent(**bd["speed_control"]),
        lead_pair=ScoreComponent(**bd["lead_pair"]),
    )
    analysis = TeamAnalysisResponse(
        valid=report["valid"],
        issues=report["issues"],
        roles=report["roles"],
        weaknesses=report["weaknesses"],
        resistances=report["resistances"],
        coverage=CoverageResult(**report["coverage"]),
        speed_control_archetype=report.get("speed_control_archetype", "none"),
    )
    return ScoreResponse(score=scoring["score"], breakdown=breakdown, analysis=analysis)
