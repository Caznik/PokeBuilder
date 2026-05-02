# src/api/routes/generation.py
"""Team generation API route."""

from fastapi import APIRouter, HTTPException

from ..models.generation import (
    GenerateRequest,
    GenerationMember,
    GenerationResponse,
    TeamAnalysis,
    TeamResult,
)
from ..models.team import CoverageResult
from ..models.scoring import ScoreBreakdown, ScoreComponent
from ..services.team_generator import generate_teams
from ..db import get_db_connection

router = APIRouter(prefix="/team", tags=["team"])


@router.post("/generate", response_model=GenerationResponse)
def generate_team_endpoint(body: GenerateRequest = GenerateRequest()):
    """Generate valid competitive Pokémon teams using guided random sampling.

    Args:
        body: Optional request body with include/exclude constraints.

    Returns:
        GenerationResponse with up to MAX_RESULTS valid teams, each with a
        score, member list, and full analysis. Also reports total candidates
        generated and how many passed validation.
    """
    try:
        with get_db_connection() as conn:
            result = generate_teams(conn, body.constraints)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    teams = []
    for t in result["teams"]:
        members = [GenerationMember(**m) for m in t["members"]]
        a = t["analysis"]
        analysis = TeamAnalysis(
            valid=a["valid"],
            issues=a["issues"],
            roles=a["roles"],
            weaknesses=a["weaknesses"],
            resistances=a["resistances"],
            coverage=CoverageResult(**a["coverage"]),
            speed_control_archetype=a.get("speed_control_archetype", "none"),
        )
        bd = t["breakdown"]
        breakdown = ScoreBreakdown(
            coverage=ScoreComponent(**bd["coverage"]),
            defensive=ScoreComponent(**bd["defensive"]),
            role=ScoreComponent(**bd["role"]),
            speed_control=ScoreComponent(**bd["speed_control"]),
            lead_pair=ScoreComponent(**bd["lead_pair"]),
        )
        teams.append(TeamResult(
            score=t["score"],
            breakdown=breakdown,
            members=members,
            analysis=analysis,
        ))

    return GenerationResponse(
        teams=teams,
        generated=result["generated"],
        valid_found=result["valid_found"],
    )
