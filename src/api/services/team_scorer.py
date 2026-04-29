# src/api/services/team_scorer.py
"""Team scoring engine: VGC doubles component scores and weighted aggregation."""

from itertools import combinations

from ..models.team import PokemonBuild
from .role_service import TAILWIND_SPEED_THRESHOLD, TR_SPEED_THRESHOLD, detect_roles
from .team_validator import TEAM_RULES, _RULE_TO_ROLE

WEIGHTS: dict[str, float] = {
    "coverage":      1.0,
    "defensive":     1.5,
    "role":          1.2,
    "speed_control": 1.3,
    "lead_pair":     1.0,
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
    """Score role balance against VGC doubles TEAM_RULES minimums.

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


def compute_speed_control_score(report: dict, builds: list[PokemonBuild]) -> dict:
    """Score speed control quality for VGC doubles.

    Checks whether the team has a speed control setter (Tailwind or Trick Room)
    and whether the rest of the team's speed stats align with that archetype.

    Args:
        report: Analysis dict from analyze_team.
        builds: List of PokemonBuild (typically 6).

    Returns:
        Dict with keys ``score`` (float, 0–1) and ``reason`` (str).
    """
    tailwind_setters = report["roles"].get("tailwind_setter", 0)
    tr_setters = report["roles"].get("trick_room_setter", 0)

    if tailwind_setters == 0 and tr_setters == 0:
        return {"score": 0.0, "reason": "no speed control"}

    if tailwind_setters >= 1 and tr_setters >= 1:
        return {"score": 1.0, "reason": "hybrid speed control (Tailwind + TR)"}

    if tailwind_setters >= 1:
        fast = sum(1 for b in builds if b.stats["speed"] >= TAILWIND_SPEED_THRESHOLD)
        score = 0.5 + 0.5 * (fast / len(builds))
        return {"score": score, "reason": f"Tailwind team, {fast} fast members"}

    # tr_setters >= 1
    slow = sum(1 for b in builds if b.stats["speed"] <= TR_SPEED_THRESHOLD)
    score = 0.5 + 0.5 * (slow / len(builds))
    return {"score": score, "reason": f"Trick Room team, {slow} slow members"}


def compute_lead_pair_score(builds: list[PokemonBuild]) -> dict:
    """Score the quality of viable lead pairs in the roster.

    A lead pair is viable when one member has a disruption role (Fake Out or
    redirector) and the other has a role that benefits from disruption
    (physical_attacker, special_attacker, or speed_control).

    Args:
        builds: List of PokemonBuild (typically 6).

    Returns:
        Dict with keys ``score`` (0.0 | 0.6 | 0.8 | 1.0) and ``reason`` (str).
    """
    viable_pairs = 0
    for a, b in combinations(builds, 2):
        roles_a = set(detect_roles(a))
        roles_b = set(detect_roles(b))
        combined = roles_a | roles_b
        has_disruption = "disruption" in combined
        has_attacker_or_sc = bool(
            combined & {"physical_attacker", "special_attacker", "speed_control"}
        )
        if has_disruption and has_attacker_or_sc:
            viable_pairs += 1

    if viable_pairs == 0:
        return {"score": 0.0, "reason": "no viable lead pair"}
    elif viable_pairs == 1:
        return {"score": 0.6, "reason": "1 viable lead pair"}
    elif viable_pairs == 2:
        return {"score": 0.8, "reason": "2 viable lead pairs"}
    else:
        return {"score": 1.0, "reason": f"{viable_pairs} viable lead pairs"}


def score_team(report: dict, builds: list[PokemonBuild]) -> dict:
    """Compute a weighted aggregate quality score for a VGC doubles team.

    Args:
        report: Analysis dict from analyze_team.
        builds: List of PokemonBuild used to compute doubles-specific scores.

    Returns:
        Dict with keys:
          - ``score``: float in [0.0, 10.0], rounded to 2 decimals.
          - ``breakdown``: dict mapping component name → {score, reason}.
    """
    breakdown = {
        "coverage":      compute_coverage_score(report),
        "defensive":     compute_defensive_score(report),
        "role":          compute_role_score(report),
        "speed_control": compute_speed_control_score(report, builds),
        "lead_pair":     compute_lead_pair_score(builds),
    }
    weighted_sum = sum(WEIGHTS[k] * breakdown[k]["score"] for k in breakdown)
    total_weight = sum(WEIGHTS.values())
    score = round((weighted_sum / total_weight) * 10, 2)
    return {"score": score, "breakdown": breakdown}
