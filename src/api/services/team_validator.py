# src/api/services/team_validator.py
"""Team validation against a configurable role rule set."""

from ..models.team import PokemonBuild
from .role_service import detect_roles

ALL_ROLES = (
    "physical_sweeper", "special_sweeper", "tank",
    "hazard_setter", "hazard_removal", "pivot", "support",
)

TEAM_RULES: dict[str, int] = {
    "min_physical_attacker": 1,
    "min_special_attacker":  1,
    "min_tank":              1,
    "min_hazard_setter":     1,
    "min_pivot":             1,
}

_RULE_TO_ROLE: dict[str, str] = {
    "min_physical_attacker": "physical_sweeper",
    "min_special_attacker":  "special_sweeper",
    "min_tank":              "tank",
    "min_hazard_setter":     "hazard_setter",
    "min_pivot":             "pivot",
}

_RULE_LABEL: dict[str, str] = {
    "min_physical_attacker": "physical attacker",
    "min_special_attacker":  "special attacker",
    "min_tank":              "tank",
    "min_hazard_setter":     "hazard setter",
    "min_pivot":             "pivot",
}


def validate_team(builds: list[PokemonBuild]) -> dict:
    """Validate a team against TEAM_RULES and return role counts.

    Args:
        builds: List of PokemonBuild (typically 6).

    Returns:
        Dict with keys: ``valid`` (bool), ``issues`` (list[str]),
        ``roles`` (dict[str, int]).
    """
    role_counts: dict[str, int] = {r: 0 for r in ALL_ROLES}
    for build in builds:
        for role in detect_roles(build):
            if role in role_counts:
                role_counts[role] += 1

    issues: list[str] = []
    for rule, minimum in TEAM_RULES.items():
        role = _RULE_TO_ROLE[rule]
        if role_counts.get(role, 0) < minimum:
            label = _RULE_LABEL[rule]
            issues.append(f"Missing {label} (need ≥ {minimum})")

    return {
        "valid":  len(issues) == 0,
        "issues": issues,
        "roles":  role_counts,
    }
