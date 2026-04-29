# src/api/services/team_analysis.py
"""Top-level team analysis: combines all sub-analyses into one report."""

from ..models.team import PokemonBuild
from .team_validator import validate_team
from .weakness_service import analyze_weaknesses
from .coverage_service import analyze_coverage


def _compute_speed_control_archetype(roles: dict[str, int]) -> str:
    """Return the team's speed control archetype label.

    Args:
        roles: Role counts dict from validate_team.

    Returns:
        One of: "tailwind", "trick_room", "hybrid", "none".
    """
    has_tailwind = roles.get("tailwind_setter", 0) >= 1
    has_tr = roles.get("trick_room_setter", 0) >= 1
    if has_tailwind and has_tr:
        return "hybrid"
    if has_tailwind:
        return "tailwind"
    if has_tr:
        return "trick_room"
    return "none"


def analyze_team(builds: list[PokemonBuild]) -> dict:
    """Produce a full strategic analysis for a VGC doubles team.

    Args:
        builds: List of PokemonBuild (typically 6).

    Returns:
        Dict with keys: valid, issues, roles, weaknesses, resistances,
        coverage, speed_control_archetype.
    """
    validation = validate_team(builds)
    weaknesses = analyze_weaknesses(builds)
    coverage   = analyze_coverage(builds)

    return {
        "valid":                   validation["valid"],
        "issues":                  validation["issues"],
        "roles":                   validation["roles"],
        "weaknesses":              weaknesses["weaknesses"],
        "resistances":             weaknesses["resistances"],
        "coverage":                coverage,
        "speed_control_archetype": _compute_speed_control_archetype(validation["roles"]),
    }
