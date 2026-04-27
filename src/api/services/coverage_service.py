# src/api/services/coverage_service.py
"""Offensive move-type coverage analysis across a team."""

from .type_service import all_multipliers_against, get_all_attacker_types
from ..models.team import PokemonBuild


def analyze_coverage(builds: list[PokemonBuild]) -> dict:
    """Determine which defending types the team can hit super-effectively.

    Only damaging moves (physical / special) contribute to coverage.
    For each move type in the team, we check if it scores > 1.0 against
    any of the 18 defender types.

    Args:
        builds: List of PokemonBuild representing the team.

    Returns:
        Dict with:
          ``covered_types`` — defender types hit super-effectively by ≥ 1 move
          ``missing_types`` — the remaining defender types
    """
    # Collect unique move types from damaging moves
    move_types: set[str] = set()
    for build in builds:
        for move in build.moves:
            if move.category != "status":
                move_types.add(move.type)

    all_types = get_all_attacker_types()  # sorted list of all 18 type names
    covered: set[str] = set()

    for move_type in move_types:
        # all_multipliers_against(defending_type) — pass as single-element list
        for defender in all_types:
            multipliers = all_multipliers_against([defender])
            if multipliers.get(move_type, 1.0) > 1.0:
                covered.add(defender)

    missing = sorted(t for t in all_types if t not in covered)
    return {
        "covered_types": sorted(covered),
        "missing_types": missing,
    }
