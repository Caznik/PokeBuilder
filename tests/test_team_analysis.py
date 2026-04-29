# tests/test_team_analysis.py
"""Unit tests for the analyze_team combiner."""

import pytest
from unittest.mock import patch, MagicMock

from src.api.models.team import PokemonBuild
from src.api.services.team_analysis import analyze_team

BASE = {"hp": 250, "attack": 200, "defense": 150,
        "sp_attack": 150, "sp_defense": 150, "speed": 200}

BUILDS = [
    PokemonBuild("garchomp", 1, ["dragon", "ground"], "jolly", None, None, BASE, [])
    for _ in range(6)
]

FAKE_VALIDATION = {
    "valid":  False,
    "issues": ["Missing tank"],
    "roles":  {"physical_sweeper": 2, "special_sweeper": 0, "tank": 0,
               "hazard_setter": 1, "hazard_removal": 0, "pivot": 1, "support": 0},
}
FAKE_WEAKNESSES = {
    "weaknesses":  {"ice": 4, "fairy": 2},
    "resistances": {"fire": 3},
}
FAKE_COVERAGE = {
    "covered_types": ["grass", "steel"],
    "missing_types": ["water", "fairy"],
}


def _run(builds=BUILDS):
    with patch("src.api.services.team_analysis.validate_team",
               return_value=FAKE_VALIDATION) as mock_val, \
         patch("src.api.services.team_analysis.analyze_weaknesses",
               return_value=FAKE_WEAKNESSES) as mock_weak, \
         patch("src.api.services.team_analysis.analyze_coverage",
               return_value=FAKE_COVERAGE) as mock_cov:
        result = analyze_team(builds)
    return result, mock_val, mock_weak, mock_cov


class TestAnalyzeTeam:

    def test_calls_validate_team(self):
        _, mock_val, _, _ = _run()
        mock_val.assert_called_once_with(BUILDS)

    def test_calls_analyze_weaknesses(self):
        _, _, mock_weak, _ = _run()
        mock_weak.assert_called_once_with(BUILDS)

    def test_calls_analyze_coverage(self):
        _, _, _, mock_cov = _run()
        mock_cov.assert_called_once_with(BUILDS)

    def test_valid_propagated(self):
        result, *_ = _run()
        assert result["valid"] == FAKE_VALIDATION["valid"]

    def test_issues_propagated(self):
        result, *_ = _run()
        assert result["issues"] == FAKE_VALIDATION["issues"]

    def test_roles_propagated(self):
        result, *_ = _run()
        assert result["roles"] == FAKE_VALIDATION["roles"]

    def test_weaknesses_propagated(self):
        result, *_ = _run()
        assert result["weaknesses"] == FAKE_WEAKNESSES["weaknesses"]

    def test_resistances_propagated(self):
        result, *_ = _run()
        assert result["resistances"] == FAKE_WEAKNESSES["resistances"]

    def test_coverage_propagated(self):
        result, *_ = _run()
        assert result["coverage"] == FAKE_COVERAGE

    def test_all_expected_keys_present(self):
        result, *_ = _run()
        for key in ("valid", "issues", "roles", "weaknesses", "resistances", "coverage"):
            assert key in result, f"Missing key: {key}"


class TestSpeedControlArchetype:
    """Tests for speed_control_archetype in the analyze_team output."""

    def _run(self, role_overrides=None):
        from unittest.mock import patch, MagicMock
        from src.api.services.team_analysis import analyze_team
        roles = {
            "physical_attacker": 1, "special_attacker": 1, "tank": 1,
            "tailwind_setter": 0, "trick_room_setter": 0,
            "fake_out_user": 1, "redirector": 0, "spread_attacker": 1,
            "support": 0, "speed_control": 0, "disruption": 1,
        }
        if role_overrides:
            roles.update(role_overrides)
        with (
            patch("src.api.services.team_analysis.validate_team",
                  return_value={"valid": True, "issues": [], "roles": roles}),
            patch("src.api.services.team_analysis.analyze_weaknesses",
                  return_value={"weaknesses": {}, "resistances": {}}),
            patch("src.api.services.team_analysis.analyze_coverage",
                  return_value={"covered_types": [], "missing_types": []}),
        ):
            return analyze_team([MagicMock()] * 6)

    def test_analyze_team_returns_speed_control_archetype_key(self):
        result = self._run()
        assert "speed_control_archetype" in result

    def test_tailwind_only_returns_tailwind(self):
        result = self._run({"tailwind_setter": 1, "trick_room_setter": 0, "speed_control": 1})
        assert result["speed_control_archetype"] == "tailwind"

    def test_trick_room_only_returns_trick_room(self):
        result = self._run({"tailwind_setter": 0, "trick_room_setter": 1, "speed_control": 1})
        assert result["speed_control_archetype"] == "trick_room"

    def test_both_returns_hybrid(self):
        result = self._run({"tailwind_setter": 1, "trick_room_setter": 1, "speed_control": 2})
        assert result["speed_control_archetype"] == "hybrid"

    def test_neither_returns_none_string(self):
        result = self._run({"tailwind_setter": 0, "trick_room_setter": 0, "speed_control": 0})
        assert result["speed_control_archetype"] == "none"
