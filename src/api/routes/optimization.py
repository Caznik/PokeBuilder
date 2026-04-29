# src/api/routes/optimization.py
"""Team optimization API route."""

from fastapi import APIRouter, HTTPException

from ..models.generation import GenerationMember, TeamAnalysis, TeamResult
from ..models.optimization import OptimizeRequest, OptimizationResponse
from ..models.scoring import ScoreBreakdown, ScoreComponent
from ..models.team import CoverageResult
from ..services.team_optimizer import optimize_team
from ..db import get_db_connection

router = APIRouter(prefix="/team", tags=["team"])


@router.post("/optimize", response_model=OptimizationResponse)
def optimize_team_endpoint(body: OptimizeRequest = OptimizeRequest()):
    """Evolve a population of competitive teams using a Genetic Algorithm.

    Args:
        body: Optional request body with constraints, population_size, generations.

    Returns:
        OptimizationResponse with best_teams, generations_run, initial_population,
        and evaluations count.
    """
    try:
        with get_db_connection() as conn:
            result = optimize_team(
                conn,
                constraints=body.constraints,
                population_size=body.population_size,
                generations=body.generations,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    teams = []
    for t in result["best_teams"]:
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

    return OptimizationResponse(
        best_teams=teams,
        generations_run=result["generations_run"],
        initial_population=result["initial_population"],
        evaluations=result["evaluations"],
    )
