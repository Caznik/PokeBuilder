# src/api/services/team_scorer.py
"""Team scoring engine: component scores and weighted aggregation."""

from ..models.team import PokemonBuild
from .role_service import SPEED_THRESHOLD, PRIORITY_MOVES
from .team_validator import TEAM_RULES, _RULE_TO_ROLE

WEIGHTS: dict[str, float] = {
    "coverage":  1.0,
    "defensive": 1.5,
    "role":      1.2,
    "speed":     1.0,
}


def compute_coverage_score(report: dict) -> dict:
    """Score offensive type coverage on a 0–1 scale.

    Args:
        report: Analysis dict from analyze_team.

    Returns:
        Dict with keys ``score`` (float, 0–1) and ``reason`` (str).
    """
    covered = len(report["coverage"]["covered_types"])
    missing = report["coverage"]["missing_types"]
    score = covered / 18

    if not missing:
        reason = "covers all 18 types"
    else:
        reason = f"missing {', '.join(sorted(missing))}"

    return {"score": score, "reason": reason}


def compute_defensive_score(report: dict) -> dict:
    """Score defensive resilience based on shared type weaknesses.

    Args:
        report: Analysis dict from analyze_team.

    Returns:
        Dict with keys ``score`` (float, 0–1) and ``reason`` (str).
    """
    weaknesses = report["weaknesses"]
    worst_type = max(weaknesses, key=weaknesses.get) if weaknesses else None
    worst_count = weaknesses[worst_type] if worst_type else 0
    score = max(0.0, 1.0 - worst_count * 0.2)

    if not weaknesses:
        reason = "no shared weaknesses"
    else:
        reason = f"{worst_count} Pokémon weak to {worst_type}"

    return {"score": score, "reason": reason}


def compute_role_score(report: dict) -> dict:
    """Score role balance against TEAM_RULES minimums.

    Args:
        report: Analysis dict from analyze_team.

    Returns:
        Dict with keys ``score`` (float, 0–1) and ``reason`` (str).
    """
    rules_met = sum(
        1 for rule, minimum in TEAM_RULES.items()
        if report["roles"].get(_RULE_TO_ROLE[rule], 0) >= minimum
    )
    score = rules_met / len(TEAM_RULES)

    if not report["issues"]:
        reason = "all role minimums met"
    else:
        reason = "; ".join(report["issues"])

    return {"score": score, "reason": reason}


def compute_speed_score(builds: list[PokemonBuild]) -> dict:
    """Score speed control via fast Pokémon and priority move users.

    Args:
        builds: List of PokemonBuild (typically 6).

    Returns:
        Dict with keys ``score`` (float, 0 | 0.5 | 1.0) and ``reason`` (str).
    """
    fast = sum(1 for b in builds if b.stats["speed"] >= SPEED_THRESHOLD)
    priority = sum(
        1 for b in builds
        if any(m.name in PRIORITY_MOVES for m in b.moves)
    )

    if fast == 0 and priority == 0:
        score, reason = 0.0, "no fast Pokémon and no priority moves"
    elif fast >= 2 or (fast >= 1 and priority >= 1):
        score = 1.0
        reason = f"{fast} fast Pokémon, {priority} priority user(s)"
    else:
        score = 0.5
        reason = f"limited speed control ({fast} fast, {priority} priority)"

    return {"score": score, "reason": reason}


def score_team(report: dict, builds: list[PokemonBuild]) -> dict:
    """Compute a weighted aggregate quality score for a team.

    Args:
        report: Analysis dict from analyze_team.
        builds: List of PokemonBuild used to compute speed score.

    Returns:
        Dict with keys:
          - ``score``: float in [0.0, 10.0], rounded to 2 decimals.
          - ``breakdown``: dict mapping component name → {score, reason}.
    """
    breakdown = {
        "coverage":  compute_coverage_score(report),
        "defensive": compute_defensive_score(report),
        "role":      compute_role_score(report),
        "speed":     compute_speed_score(builds),
    }
    weighted_sum = sum(WEIGHTS[k] * breakdown[k]["score"] for k in breakdown)
    total_weight = sum(WEIGHTS.values())
    score = round((weighted_sum / total_weight) * 10, 2)
    return {"score": score, "breakdown": breakdown}
