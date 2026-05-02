# src/api/services/team_validator.py
"""Team validation against VGC doubles role rule set."""

from ..models.team import PokemonBuild
from .role_service import detect_roles

ALL_ROLES = (
    "physical_attacker", "special_attacker", "tank",
    "tailwind_setter", "trick_room_setter",
    "fake_out_user", "redirector", "spread_attacker",
    "support",
    "speed_control", "disruption",
)

TEAM_RULES: dict[str, int] = {
    "min_physical_attacker": 1,
    "min_special_attacker":  1,
    "min_speed_control":     1,
    "min_disruption":        1,
}

_RULE_TO_ROLE: dict[str, str] = {
    "min_physical_attacker": "physical_attacker",
    "min_special_attacker":  "special_attacker",
    "min_speed_control":     "speed_control",
    "min_disruption":        "disruption",
}

_RULE_LABEL: dict[str, str] = {
    "min_physical_attacker": "physical attacker",
    "min_special_attacker":  "special attacker",
    "min_speed_control":     "speed control (Tailwind or Trick Room setter)",
    "min_disruption":        "disruption (Fake Out or redirector)",
}


def validate_team(builds: list[PokemonBuild]) -> dict:
    """Validate a team against VGC doubles TEAM_RULES and return role counts.

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
