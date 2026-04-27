# src/api/services/weakness_service.py
"""Type weakness and resistance analysis across a team."""

from collections import defaultdict

from .type_service import all_multipliers_against
from ..models.team import PokemonBuild


def analyze_weaknesses(builds: list[PokemonBuild]) -> dict:
    """Compute how many team members are weak or resistant to each type.

    Args:
        builds: List of PokemonBuild representing the team.

    Returns:
        Dict with:
          ``weaknesses``  — {type_name: count} for multiplier > 1.0
          ``resistances`` — {type_name: count} for multiplier < 1.0 (incl. 0)
    """
    weak_counts: dict[str, int] = defaultdict(int)
    resist_counts: dict[str, int] = defaultdict(int)

    for build in builds:
        if not build.types:
            continue
        multipliers = all_multipliers_against(build.types)
        for type_name, mult in multipliers.items():
            if mult > 1.0:
                weak_counts[type_name] += 1
            elif mult < 1.0:
                resist_counts[type_name] += 1

    return {
        "weaknesses":  dict(weak_counts),
        "resistances": dict(resist_counts),
    }
