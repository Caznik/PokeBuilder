# src/api/services/team_analysis.py
"""Top-level team analysis: combines all sub-analyses into one report."""

from ..models.team import PokemonBuild
from .team_validator import validate_team
from .weakness_service import analyze_weaknesses
from .coverage_service import analyze_coverage


def analyze_team(builds: list[PokemonBuild]) -> dict:
    """Produce a full strategic analysis for a team of Pokémon builds.

    Args:
        builds: List of PokemonBuild (typically 6).

    Returns:
        Dict with keys: valid, issues, roles, weaknesses, resistances, coverage.
    """
    validation  = validate_team(builds)
    weaknesses  = analyze_weaknesses(builds)
    coverage    = analyze_coverage(builds)

    return {
        "valid":       validation["valid"],
        "issues":      validation["issues"],
        "roles":       validation["roles"],
        "weaknesses":  weaknesses["weaknesses"],
        "resistances": weaknesses["resistances"],
        "coverage":    coverage,
    }
