# src/api/routes/counter.py
"""Counter team API route — beam search against current meta."""

from fastapi import APIRouter, HTTPException

from ..db import get_db_connection
from ..models.counter import CounterRequest, CounterResponse, MetaPokemon, MetaSnapshot
from ..models.generation import GenerationMember, TeamAnalysis, TeamResult
from ..models.scoring import ScoreBreakdown, ScoreComponent
from ..models.team import CoverageResult
from ..services.counter_optimizer import suggest_counter_team

router = APIRouter(prefix="/team", tags=["team"])


@router.post("/counter", response_model=CounterResponse)
def counter_team_endpoint(body: CounterRequest):
    """Suggest teams proven to counter the current meta using beam search.

    Args:
        body: regulation_id (required), beam_width, meta_top_n.

    Returns:
        CounterResponse with best_teams, algorithm, meta_snapshot,
        and replays_analyzed count.
    """
    try:
        with get_db_connection() as conn:
            result = suggest_counter_team(
                conn,
                regulation_id=body.regulation_id,
                beam_width=body.beam_width,
                meta_top_n=body.meta_top_n,
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

    snapshot = MetaSnapshot(
        top_pokemon=[MetaPokemon(**p) for p in result["meta_snapshot"]["top_pokemon"]],
        total_battles=result["meta_snapshot"]["total_battles"],
    )
    return CounterResponse(
        best_teams=teams,
        algorithm=result["algorithm"],
        meta_snapshot=snapshot,
        replays_analyzed=result["replays_analyzed"],
    )
