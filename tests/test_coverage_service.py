# tests/test_coverage_service.py
"""Unit tests for offensive coverage analysis."""

import pytest
from contextlib import ExitStack
from unittest.mock import patch
from src.api.models.team import MoveDetail, PokemonBuild
from src.api.services.coverage_service import analyze_coverage

ALL_TYPES = [
    "normal", "fire", "water", "electric", "grass", "ice",
    "fighting", "poison", "ground", "flying", "psychic", "bug",
    "rock", "ghost", "dragon", "dark", "steel", "fairy",
]

BASE = {"hp": 250, "attack": 200, "defense": 150,
        "sp_attack": 150, "sp_defense": 150, "speed": 200}


def _build(moves):
    return PokemonBuild("x", 1, ["normal"], None, None, None, BASE, moves)


def _phys(type_):
    return MoveDetail("tackle", type_, "physical")


def _status(type_="poison"):
    return MoveDetail("toxic", type_, "status")


# ---------------------------------------------------------------------------
# all_multipliers_against([defender]) returns {attacker: mult} for that defender.
# We model a realistic subset: fire is super-effective vs grass/ice/bug/steel.
# ---------------------------------------------------------------------------

FIRE_COVERS = {"grass", "ice", "bug", "steel"}
WATER_COVERS = {"fire", "ground", "rock"}


def _multipliers_for(defender_types: list[str]) -> dict[str, float]:
    """Fake all_multipliers_against result for a single defender type."""
    defender = defender_types[0]
    result = {t: 1.0 for t in ALL_TYPES}
    if defender in FIRE_COVERS:
        result["fire"] = 2.0
    if defender in WATER_COVERS:
        result["water"] = 2.0
    return result


def _patched(fn=_multipliers_for):
    """Return an ExitStack that mocks both type_service helpers."""
    stack = ExitStack()
    stack.enter_context(patch(
        "src.api.services.coverage_service.get_all_attacker_types",
        return_value=ALL_TYPES,
    ))
    stack.enter_context(patch(
        "src.api.services.coverage_service.all_multipliers_against",
        side_effect=fn,
    ))
    return stack


class TestAnalyzeCoverage:

    def test_returns_covered_and_missing_keys(self):
        with _patched():
            result = analyze_coverage([_build([_phys("fire")])])
        assert "covered_types" in result
        assert "missing_types" in result

    def test_fire_move_covers_expected_types(self):
        with _patched():
            result = analyze_coverage([_build([_phys("fire")])])
        for t in FIRE_COVERS:
            assert t in result["covered_types"], f"{t} should be covered by fire"

    def test_fire_move_does_not_cover_water(self):
        with _patched():
            result = analyze_coverage([_build([_phys("fire")])])
        assert "water" not in result["covered_types"]

    def test_status_moves_ignored(self):
        """Status moves should not contribute to coverage."""
        with _patched():
            result = analyze_coverage([_build([_status("poison")])])
        assert result["covered_types"] == []

    def test_missing_is_complement_of_covered(self):
        with _patched():
            result = analyze_coverage([_build([_phys("fire")])])
        covered = set(result["covered_types"])
        missing = set(result["missing_types"])
        assert covered | missing == set(ALL_TYPES)
        assert covered & missing == set()

    def test_no_moves_means_no_coverage(self):
        with _patched():
            result = analyze_coverage([_build([])])
        assert result["covered_types"] == []
        assert set(result["missing_types"]) == set(ALL_TYPES)

    def test_multiple_pokemon_moves_merged(self):
        """Fire + water moves together should cover both sets."""
        with _patched():
            result = analyze_coverage([
                _build([_phys("fire")]),
                _build([_phys("water")]),
            ])
        for t in FIRE_COVERS | WATER_COVERS:
            assert t in result["covered_types"], f"{t} should be covered"

    def test_duplicate_move_types_deduplicated(self):
        """Two Pokémon with the same move type should not double-count coverage."""
        with _patched():
            result1 = analyze_coverage([_build([_phys("fire")])])
            result2 = analyze_coverage([_build([_phys("fire")]),
                                        _build([_phys("fire")])])
        assert set(result1["covered_types"]) == set(result2["covered_types"])
