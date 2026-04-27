# tests/test_team_validator.py
"""Unit tests for team validator."""

import pytest
from unittest.mock import patch
from src.api.models.team import MoveDetail, PokemonBuild
from src.api.services.team_validator import validate_team

BASE = {"hp": 250, "attack": 200, "defense": 150,
        "sp_attack": 150, "sp_defense": 150, "speed": 200}


def _build(roles):
    """Create a fake build whose detect_roles will return the given list."""
    return PokemonBuild("x", 1, ["normal"], None, None, None, BASE, [])


def _team_with_roles(role_lists: list[list[str]]) -> list[PokemonBuild]:
    """Return a list of builds mocked so detect_roles returns the given roles."""
    return [_build(r) for r in role_lists]


def _validate(role_lists):
    builds = _team_with_roles(role_lists)
    side_effects = role_lists[:]
    with patch("src.api.services.team_validator.detect_roles",
               side_effect=side_effects):
        return validate_team(builds)


class TestValidTeam:

    def test_valid_team_returns_valid_true(self):
        result = _validate([
            ["physical_sweeper"],
            ["special_sweeper"],
            ["tank"],
            ["hazard_setter"],
            ["pivot"],
            ["support"],
        ])
        assert result["valid"] is True
        assert result["issues"] == []

    def test_one_pokemon_can_cover_multiple_rules(self):
        result = _validate([
            ["physical_sweeper", "hazard_setter"],
            ["special_sweeper", "pivot"],
            ["tank"],
            ["support"],
            ["physical_sweeper"],
            ["special_sweeper"],
        ])
        assert result["valid"] is True


class TestInvalidTeam:

    def test_missing_physical_attacker(self):
        result = _validate([
            ["special_sweeper"],
            ["special_sweeper"],
            ["tank"],
            ["hazard_setter"],
            ["pivot"],
            ["support"],
        ])
        assert result["valid"] is False
        assert any("physical" in i.lower() for i in result["issues"])

    def test_missing_special_attacker(self):
        result = _validate([
            ["physical_sweeper"],
            ["physical_sweeper"],
            ["tank"],
            ["hazard_setter"],
            ["pivot"],
            ["support"],
        ])
        assert result["valid"] is False
        assert any("special" in i.lower() for i in result["issues"])

    def test_missing_tank(self):
        result = _validate([
            ["physical_sweeper"],
            ["special_sweeper"],
            ["physical_sweeper"],
            ["hazard_setter"],
            ["pivot"],
            ["support"],
        ])
        assert result["valid"] is False
        assert any("tank" in i.lower() for i in result["issues"])

    def test_missing_hazard_setter(self):
        result = _validate([
            ["physical_sweeper"],
            ["special_sweeper"],
            ["tank"],
            ["pivot"],
            ["pivot"],
            ["support"],
        ])
        assert result["valid"] is False
        assert any("hazard setter" in i.lower() for i in result["issues"])

    def test_missing_pivot(self):
        result = _validate([
            ["physical_sweeper"],
            ["special_sweeper"],
            ["tank"],
            ["hazard_setter"],
            ["support"],
            ["support"],
        ])
        assert result["valid"] is False
        assert any("pivot" in i.lower() for i in result["issues"])

    def test_multiple_issues_reported(self):
        result = _validate([
            ["support"],
            ["support"],
            ["support"],
            ["support"],
            ["support"],
            ["support"],
        ])
        assert result["valid"] is False
        assert len(result["issues"]) >= 3


class TestRolesAggregated:

    def test_roles_counts_are_correct(self):
        result = _validate([
            ["physical_sweeper", "pivot"],
            ["special_sweeper"],
            ["tank", "hazard_setter"],
            ["physical_sweeper"],
            ["pivot"],
            ["support"],
        ])
        assert result["roles"]["physical_sweeper"] == 2
        assert result["roles"]["special_sweeper"] == 1
        assert result["roles"]["pivot"] == 2
        assert result["roles"]["hazard_setter"] == 1
        assert result["roles"]["tank"] == 1

    def test_all_role_keys_present_even_if_zero(self):
        result = _validate([[], [], [], [], [], []])
        for key in ("physical_sweeper", "special_sweeper", "tank",
                    "hazard_setter", "hazard_removal", "pivot", "support"):
            assert key in result["roles"]
