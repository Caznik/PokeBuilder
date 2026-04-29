# tests/test_team_validator.py
"""Unit tests for VGC doubles team validation."""

import pytest
from unittest.mock import patch
from src.api.services.team_validator import validate_team, TEAM_RULES, ALL_ROLES
from src.api.models.team import PokemonBuild, MoveDetail


def _build(roles_to_assign):
    """Create a mock build that will detect the given roles."""
    return PokemonBuild(
        pokemon_name="test", set_id=1, types=["normal"],
        nature="hardy", ability=None, item=None,
        stats={"hp": 100, "attack": 100, "defense": 100,
               "sp_attack": 100, "sp_defense": 100, "speed": 100},
        moves=[],
    )


def _team_with_roles(roles_per_build: list[list[str]]) -> list:
    """Build a list of PokemonBuild mocks, patching detect_roles per build."""
    return [_build(r) for r in roles_per_build]


class TestTeamRulesConstants:
    def test_team_rules_requires_physical_attacker(self):
        assert "min_physical_attacker" in TEAM_RULES

    def test_team_rules_requires_special_attacker(self):
        assert "min_special_attacker" in TEAM_RULES

    def test_team_rules_requires_speed_control(self):
        assert "min_speed_control" in TEAM_RULES

    def test_team_rules_requires_disruption(self):
        assert "min_disruption" in TEAM_RULES

    def test_team_rules_does_not_require_hazard_setter(self):
        assert "min_hazard_setter" not in TEAM_RULES

    def test_team_rules_does_not_require_pivot(self):
        assert "min_pivot" not in TEAM_RULES

    def test_all_roles_includes_tailwind_setter(self):
        assert "tailwind_setter" in ALL_ROLES

    def test_all_roles_includes_trick_room_setter(self):
        assert "trick_room_setter" in ALL_ROLES

    def test_all_roles_includes_fake_out_user(self):
        assert "fake_out_user" in ALL_ROLES

    def test_all_roles_includes_speed_control(self):
        assert "speed_control" in ALL_ROLES

    def test_all_roles_includes_disruption(self):
        assert "disruption" in ALL_ROLES

    def test_all_roles_does_not_include_hazard_setter(self):
        assert "hazard_setter" not in ALL_ROLES

    def test_all_roles_does_not_include_pivot(self):
        assert "pivot" not in ALL_ROLES


class TestValidateTeam:
    def test_valid_vgc_team_passes(self):
        role_sets = [
            ["physical_attacker"],
            ["special_attacker"],
            ["tailwind_setter", "speed_control"],
            ["fake_out_user", "disruption"],
            ["tank"],
            ["spread_attacker"],
        ]
        builds = _team_with_roles(role_sets)
        with patch("src.api.services.team_validator.detect_roles",
                   side_effect=role_sets):
            result = validate_team(builds)
        assert result["valid"] is True
        assert result["issues"] == []

    def test_missing_speed_control_is_invalid(self):
        role_sets = [
            ["physical_attacker"],
            ["special_attacker"],
            ["fake_out_user", "disruption"],
            ["tank"],
            ["spread_attacker"],
            ["support"],
        ]
        builds = _team_with_roles(role_sets)
        with patch("src.api.services.team_validator.detect_roles",
                   side_effect=role_sets):
            result = validate_team(builds)
        assert result["valid"] is False
        assert any("speed control" in i.lower() for i in result["issues"])

    def test_missing_disruption_is_invalid(self):
        role_sets = [
            ["physical_attacker"],
            ["special_attacker"],
            ["tailwind_setter", "speed_control"],
            ["tank"],
            ["spread_attacker"],
            ["support"],
        ]
        builds = _team_with_roles(role_sets)
        with patch("src.api.services.team_validator.detect_roles",
                   side_effect=role_sets):
            result = validate_team(builds)
        assert result["valid"] is False
        assert any("disruption" in i.lower() for i in result["issues"])

    def test_roles_dict_contains_vgc_keys(self):
        role_sets = [
            ["physical_attacker"],
            ["special_attacker"],
            ["tailwind_setter", "speed_control"],
            ["fake_out_user", "disruption"],
            ["tank"],
            ["spread_attacker"],
        ]
        builds = _team_with_roles(role_sets)
        with patch("src.api.services.team_validator.detect_roles",
                   side_effect=role_sets):
            result = validate_team(builds)
        assert "physical_attacker" in result["roles"]
        assert "tailwind_setter" in result["roles"]
        assert "speed_control" in result["roles"]
        assert "disruption" in result["roles"]

    def test_roles_dict_does_not_contain_singles_keys(self):
        role_sets = [["physical_attacker"]] * 6
        builds = _team_with_roles(role_sets)
        with patch("src.api.services.team_validator.detect_roles",
                   side_effect=role_sets):
            result = validate_team(builds)
        assert "hazard_setter" not in result["roles"]
        assert "pivot" not in result["roles"]
        assert "physical_sweeper" not in result["roles"]

    def test_trick_room_setter_satisfies_speed_control_rule(self):
        role_sets = [
            ["physical_attacker"],
            ["special_attacker"],
            ["trick_room_setter", "speed_control"],
            ["fake_out_user", "disruption"],
            ["tank"],
            ["spread_attacker"],
        ]
        builds = _team_with_roles(role_sets)
        with patch("src.api.services.team_validator.detect_roles",
                   side_effect=role_sets):
            result = validate_team(builds)
        assert result["valid"] is True

    def test_redirector_satisfies_disruption_rule(self):
        role_sets = [
            ["physical_attacker"],
            ["special_attacker"],
            ["tailwind_setter", "speed_control"],
            ["redirector", "disruption"],
            ["tank"],
            ["spread_attacker"],
        ]
        builds = _team_with_roles(role_sets)
        with patch("src.api.services.team_validator.detect_roles",
                   side_effect=role_sets):
            result = validate_team(builds)
        assert result["valid"] is True
