# tests/test_team_scorer.py
"""Unit tests for the team scoring engine."""

import pytest

from src.api.models.team import PokemonBuild, MoveDetail
from src.api.services.team_scorer import (
    WEIGHTS,
    compute_coverage_score,
    compute_defensive_score,
    compute_role_score,
    compute_speed_score,
    score_team,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build(speed=90, move_names=()):
    moves = [MoveDetail(name=n, type="normal", category="physical") for n in move_names]
    return PokemonBuild(
        pokemon_name="test",
        set_id=1,
        types=["normal"],
        nature="hardy",
        ability="none",
        item="none",
        stats={
            "hp": 100, "attack": 100, "defense": 100,
            "sp_attack": 100, "sp_defense": 100, "speed": speed,
        },
        moves=moves,
    )


_ALL_TYPES = [
    "fire", "water", "grass", "electric", "ice", "fighting",
    "poison", "ground", "flying", "psychic", "bug", "rock",
    "ghost", "dragon", "dark", "steel", "fairy", "normal",
]


def _report(**overrides):
    base = {
        "valid": True,
        "issues": [],
        "roles": {
            "physical_sweeper": 1, "special_sweeper": 1, "tank": 1,
            "hazard_setter": 1, "pivot": 1, "hazard_removal": 0, "support": 0,
        },
        "weaknesses": {"water": 1},
        "resistances": {},
        "coverage": {"covered_types": _ALL_TYPES[:], "missing_types": []},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# compute_coverage_score
# ---------------------------------------------------------------------------

class TestComputeCoverageScore:
    def test_all_18_types_scores_1(self):
        report = _report(coverage={"covered_types": _ALL_TYPES, "missing_types": []})
        result = compute_coverage_score(report)
        assert result["score"] == pytest.approx(1.0)

    def test_all_18_types_reason(self):
        report = _report(coverage={"covered_types": _ALL_TYPES, "missing_types": []})
        result = compute_coverage_score(report)
        assert result["reason"] == "covers all 18 types"

    def test_9_types_scores_half(self):
        nine = _ALL_TYPES[:9]
        report = _report(coverage={"covered_types": nine, "missing_types": _ALL_TYPES[9:]})
        result = compute_coverage_score(report)
        assert result["score"] == pytest.approx(9 / 18)

    def test_0_types_scores_0(self):
        report = _report(coverage={"covered_types": [], "missing_types": _ALL_TYPES})
        result = compute_coverage_score(report)
        assert result["score"] == pytest.approx(0.0)

    def test_missing_types_in_reason_sorted(self):
        report = _report(coverage={
            "covered_types": ["fire"],
            "missing_types": ["ice", "fairy", "dragon"],
        })
        result = compute_coverage_score(report)
        reason = result["reason"]
        assert reason.index("dragon") < reason.index("fairy") < reason.index("ice")

    def test_reason_starts_with_missing(self):
        report = _report(coverage={"covered_types": ["fire"], "missing_types": ["ice"]})
        result = compute_coverage_score(report)
        assert result["reason"].startswith("missing")

    def test_score_and_reason_always_returned(self):
        report = _report(coverage={"covered_types": ["fire"], "missing_types": []})
        result = compute_coverage_score(report)
        assert "score" in result
        assert "reason" in result


# ---------------------------------------------------------------------------
# compute_defensive_score
# ---------------------------------------------------------------------------

class TestComputeDefensiveScore:
    def test_no_weaknesses_scores_1(self):
        result = compute_defensive_score(_report(weaknesses={}))
        assert result["score"] == pytest.approx(1.0)

    def test_no_weaknesses_reason(self):
        result = compute_defensive_score(_report(weaknesses={}))
        assert result["reason"] == "no shared weaknesses"

    def test_1_weakness_scores_08(self):
        result = compute_defensive_score(_report(weaknesses={"fire": 1}))
        assert result["score"] == pytest.approx(0.8)

    def test_2_weaknesses_scores_06(self):
        result = compute_defensive_score(_report(weaknesses={"ice": 2}))
        assert result["score"] == pytest.approx(0.6)

    def test_5_weaknesses_scores_0(self):
        result = compute_defensive_score(_report(weaknesses={"ground": 5}))
        assert result["score"] == pytest.approx(0.0)

    def test_above_5_clamped_to_0(self):
        result = compute_defensive_score(_report(weaknesses={"ground": 6}))
        assert result["score"] == pytest.approx(0.0)

    def test_uses_worst_type_for_score(self):
        result = compute_defensive_score(_report(weaknesses={"ice": 1, "fire": 3}))
        assert result["score"] == pytest.approx(1.0 - 3 * 0.2)

    def test_reason_names_worst_type_and_count(self):
        result = compute_defensive_score(_report(weaknesses={"ice": 1, "fire": 3}))
        assert "fire" in result["reason"]
        assert "3" in result["reason"]

    def test_score_and_reason_always_returned(self):
        result = compute_defensive_score(_report(weaknesses={"water": 2}))
        assert "score" in result
        assert "reason" in result


# ---------------------------------------------------------------------------
# compute_role_score
# ---------------------------------------------------------------------------

class TestComputeRoleScore:
    def test_all_rules_met_scores_1(self):
        result = compute_role_score(_report())
        assert result["score"] == pytest.approx(1.0)

    def test_all_rules_met_reason(self):
        result = compute_role_score(_report())
        assert result["reason"] == "all role minimums met"

    def test_missing_one_role_scores_4_of_5(self):
        roles = {
            "physical_sweeper": 0, "special_sweeper": 1, "tank": 1,
            "hazard_setter": 1, "pivot": 1, "hazard_removal": 0, "support": 0,
        }
        report = _report(roles=roles, valid=False,
                         issues=["Missing physical attacker (need ≥ 1)"])
        result = compute_role_score(report)
        assert result["score"] == pytest.approx(4 / 5)

    def test_issues_appear_in_reason(self):
        roles = {
            "physical_sweeper": 0, "special_sweeper": 0, "tank": 1,
            "hazard_setter": 1, "pivot": 1, "hazard_removal": 0, "support": 0,
        }
        report = _report(
            roles=roles, valid=False,
            issues=["Missing physical attacker (need ≥ 1)",
                    "Missing special attacker (need ≥ 1)"],
        )
        result = compute_role_score(report)
        assert "Missing physical attacker" in result["reason"]
        assert "Missing special attacker" in result["reason"]

    def test_no_rules_met_scores_0(self):
        roles = {r: 0 for r in [
            "physical_sweeper", "special_sweeper", "tank",
            "hazard_setter", "pivot", "hazard_removal", "support",
        ]}
        report = _report(roles=roles, valid=False,
                         issues=["i1", "i2", "i3", "i4", "i5"])
        result = compute_role_score(report)
        assert result["score"] == pytest.approx(0.0)

    def test_score_and_reason_always_returned(self):
        result = compute_role_score(_report())
        assert "score" in result
        assert "reason" in result


# ---------------------------------------------------------------------------
# compute_speed_score
# ---------------------------------------------------------------------------

class TestComputeSpeedScore:
    def test_no_fast_no_priority_scores_0(self):
        builds = [_build(speed=100)] * 6
        result = compute_speed_score(builds)
        assert result["score"] == pytest.approx(0.0)

    def test_no_fast_no_priority_reason(self):
        builds = [_build(speed=100)] * 6
        result = compute_speed_score(builds)
        assert result["reason"] == "no fast Pokémon and no priority moves"

    def test_two_fast_scores_1(self):
        builds = [_build(speed=280)] * 2 + [_build(speed=100)] * 4
        result = compute_speed_score(builds)
        assert result["score"] == pytest.approx(1.0)

    def test_one_fast_one_priority_scores_1(self):
        builds = [
            _build(speed=280),
            _build(speed=100, move_names=["extreme-speed"]),
        ] + [_build(speed=90)] * 4
        result = compute_speed_score(builds)
        assert result["score"] == pytest.approx(1.0)

    def test_one_fast_no_priority_scores_half(self):
        builds = [_build(speed=280)] + [_build(speed=100)] * 5
        result = compute_speed_score(builds)
        assert result["score"] == pytest.approx(0.5)

    def test_zero_fast_one_priority_scores_half(self):
        builds = [_build(speed=100, move_names=["bullet-punch"])] + [_build(speed=90)] * 5
        result = compute_speed_score(builds)
        assert result["score"] == pytest.approx(0.5)

    def test_half_score_reason_format(self):
        builds = [_build(speed=280)] + [_build(speed=100)] * 5
        result = compute_speed_score(builds)
        assert "1 fast" in result["reason"]
        assert "0 priority" in result["reason"]

    def test_full_score_reason_includes_counts(self):
        builds = [_build(speed=280)] * 2 + [_build(speed=100)] * 4
        result = compute_speed_score(builds)
        assert "2 fast" in result["reason"]

    def test_speed_at_threshold_counts_as_fast(self):
        builds = [_build(speed=280)] * 2 + [_build(speed=100)] * 4
        result = compute_speed_score(builds)
        assert result["score"] == pytest.approx(1.0)

    def test_speed_below_threshold_not_fast(self):
        builds = [_build(speed=279)] * 6
        result = compute_speed_score(builds)
        assert result["score"] == pytest.approx(0.0)

    def test_all_priority_moves_detected(self):
        priority_moves = [
            "extreme-speed", "sucker-punch", "bullet-punch", "mach-punch",
            "ice-shard", "aqua-jet", "vacuum-wave", "accelerock",
            "jet-punch", "thunderclap", "quick-attack", "shadow-sneak",
        ]
        for move in priority_moves:
            builds = [_build(speed=100, move_names=[move])] + [_build(speed=90)] * 5
            result = compute_speed_score(builds)
            assert result["score"] == pytest.approx(0.5), f"Expected 0.5 for {move}"

    def test_score_and_reason_always_returned(self):
        result = compute_speed_score([_build()] * 6)
        assert "score" in result
        assert "reason" in result


# ---------------------------------------------------------------------------
# score_team aggregation
# ---------------------------------------------------------------------------

class TestScoreTeam:
    def _perfect_builds(self):
        return [_build(speed=280)] * 2 + [_build(speed=100)] * 4

    def _perfect_report(self):
        return _report(weaknesses={}, coverage={"covered_types": _ALL_TYPES, "missing_types": []})

    def test_returns_score_and_breakdown(self):
        result = score_team(self._perfect_report(), self._perfect_builds())
        assert "score" in result
        assert "breakdown" in result

    def test_breakdown_has_four_components(self):
        result = score_team(self._perfect_report(), self._perfect_builds())
        assert set(result["breakdown"].keys()) == {"coverage", "defensive", "role", "speed"}

    def test_each_component_has_score_and_reason(self):
        result = score_team(self._perfect_report(), self._perfect_builds())
        for key, comp in result["breakdown"].items():
            assert "score" in comp, f"{key} missing score"
            assert "reason" in comp, f"{key} missing reason"

    def test_perfect_team_scores_10(self):
        result = score_team(self._perfect_report(), self._perfect_builds())
        assert result["score"] == pytest.approx(10.0)

    def test_score_in_0_to_10_range(self):
        result = score_team(self._perfect_report(), self._perfect_builds())
        assert 0.0 <= result["score"] <= 10.0

    def test_score_rounded_to_2_decimals(self):
        result = score_team(self._perfect_report(), self._perfect_builds())
        assert result["score"] == round(result["score"], 2)

    def test_weighted_average_formula(self):
        report = _report(
            weaknesses={"ice": 1},
            coverage={"covered_types": _ALL_TYPES, "missing_types": []},
        )
        builds = [_build(speed=280)] * 2 + [_build(speed=100)] * 4
        result = score_team(report, builds)
        # coverage=1.0, defensive=0.8 (1 weakness), role=1.0, speed=1.0
        weighted_sum = (
            WEIGHTS["coverage"] * 1.0
            + WEIGHTS["defensive"] * 0.8
            + WEIGHTS["role"] * 1.0
            + WEIGHTS["speed"] * 1.0
        )
        expected = round((weighted_sum / sum(WEIGHTS.values())) * 10, 2)
        assert result["score"] == pytest.approx(expected)

    def test_bad_team_scores_lower_than_good_team(self):
        good_report = _report(
            weaknesses={},
            coverage={"covered_types": _ALL_TYPES, "missing_types": []},
        )
        good_builds = [_build(speed=280)] * 2 + [_build(speed=100)] * 4
        good = score_team(good_report, good_builds)

        bad_roles = {r: 0 for r in [
            "physical_sweeper", "special_sweeper", "tank",
            "hazard_setter", "pivot", "hazard_removal", "support",
        ]}
        bad_report = _report(
            weaknesses={"ice": 4},
            coverage={"covered_types": ["fire"], "missing_types": _ALL_TYPES[1:]},
            roles=bad_roles,
            valid=False,
            issues=["i1", "i2", "i3", "i4", "i5"],
        )
        bad = score_team(bad_report, [_build(speed=100)] * 6)

        assert good["score"] > bad["score"]
