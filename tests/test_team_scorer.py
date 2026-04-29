# tests/test_team_scorer.py
"""Unit tests for the VGC doubles team scoring engine."""

import pytest
from src.api.models.team import PokemonBuild, MoveDetail
from src.api.services.team_scorer import (
    WEIGHTS,
    compute_coverage_score,
    compute_defensive_score,
    compute_role_score,
    compute_speed_control_score,
    compute_lead_pair_score,
    score_team,
)
from src.api.services.role_service import TAILWIND_SPEED_THRESHOLD, TR_SPEED_THRESHOLD


_PHYSICAL_MOVES = {
    "earthquake", "fake-out", "u-turn", "tackle", "rock-slide",
    "breaking-swipe", "close-combat", "extreme-speed",
}
_SPECIAL_MOVES = {
    "heat-wave", "discharge", "surf", "blizzard", "flamethrower",
    "muddy-water", "hyper-voice", "sludge-wave", "dazzling-gleam",
}


def _build(speed=200, move_names=(), attack=200, sp_attack=200):
    moves = []
    for n in move_names:
        cat = ("physical" if n in _PHYSICAL_MOVES
               else "special" if n in _SPECIAL_MOVES
               else "status")
        moves.append(MoveDetail(name=n, type="normal", category=cat))
    return PokemonBuild(
        pokemon_name="test", set_id=1, types=["normal"],
        nature="hardy", ability=None, item=None,
        stats={"hp": 200, "attack": attack, "defense": 150,
               "sp_attack": sp_attack, "sp_defense": 150, "speed": speed},
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
            "physical_attacker": 2, "special_attacker": 1, "tank": 1,
            "tailwind_setter": 1, "trick_room_setter": 0,
            "fake_out_user": 1, "redirector": 0, "spread_attacker": 2,
            "support": 0, "speed_control": 1, "disruption": 1,
        },
        "weaknesses": {},
        "resistances": {},
        "coverage": {"covered_types": _ALL_TYPES, "missing_types": []},
        "speed_control_archetype": "tailwind",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# compute_coverage_score
# ---------------------------------------------------------------------------

class TestCoverageScore:
    def test_perfect_coverage_scores_1(self):
        result = compute_coverage_score(_report())
        assert result["score"] == pytest.approx(1.0)

    def test_missing_types_reduces_score(self):
        r = _report(coverage={"covered_types": _ALL_TYPES[:9], "missing_types": _ALL_TYPES[9:]})
        result = compute_coverage_score(r)
        assert result["score"] == pytest.approx(9 / 18)

    def test_reason_lists_missing_types(self):
        r = _report(coverage={"covered_types": _ALL_TYPES[:17], "missing_types": ["fairy"]})
        result = compute_coverage_score(r)
        assert "fairy" in result["reason"]

    def test_reason_is_all_covered_when_no_missing(self):
        result = compute_coverage_score(_report())
        assert result["reason"] == "covers all 18 types"


# ---------------------------------------------------------------------------
# compute_defensive_score
# ---------------------------------------------------------------------------

class TestDefensiveScore:
    def test_no_weaknesses_scores_one(self):
        r = _report(weaknesses={})
        result = compute_defensive_score(r)
        assert result["score"] == pytest.approx(1.0)
        assert result["reason"] == "no shared weaknesses"

    def test_one_weakness_scores_point_eight(self):
        r = _report(weaknesses={"ground": 1})
        result = compute_defensive_score(r)
        assert result["score"] == pytest.approx(0.8)

    def test_five_or_more_weaknesses_clamped_to_zero(self):
        r = _report(weaknesses={"ground": 5})
        result = compute_defensive_score(r)
        assert result["score"] == pytest.approx(0.0)

    def test_reason_names_worst_type(self):
        r = _report(weaknesses={"ground": 3, "fire": 1})
        result = compute_defensive_score(r)
        assert "ground" in result["reason"]


# ---------------------------------------------------------------------------
# compute_role_score
# ---------------------------------------------------------------------------

class TestRoleScore:
    def test_all_rules_met_scores_one(self):
        result = compute_role_score(_report())
        assert result["score"] == pytest.approx(1.0)
        assert result["reason"] == "all role minimums met"

    def test_missing_speed_control_reduces_score(self):
        roles = {**_report()["roles"], "speed_control": 0}
        r = _report(roles=roles, issues=["Missing speed control (need ≥ 1)"], valid=False)
        result = compute_role_score(r)
        assert result["score"] < 1.0

    def test_reason_contains_issues_when_rules_not_met(self):
        r = _report(issues=["Missing disruption (need ≥ 1)"])
        result = compute_role_score(r)
        assert "disruption" in result["reason"]


# ---------------------------------------------------------------------------
# compute_speed_control_score
# ---------------------------------------------------------------------------

class TestSpeedControlScore:
    def test_no_setter_scores_zero(self):
        r = _report(roles={**_report()["roles"], "tailwind_setter": 0, "trick_room_setter": 0})
        builds = [_build(speed=300)] * 6
        result = compute_speed_control_score(r, builds)
        assert result["score"] == 0.0
        assert "no speed control" in result["reason"]

    def test_hybrid_tailwind_and_tr_scores_one(self):
        r = _report(roles={**_report()["roles"], "tailwind_setter": 1, "trick_room_setter": 1})
        builds = [_build(speed=200)] * 6
        result = compute_speed_control_score(r, builds)
        assert result["score"] == 1.0
        assert "hybrid" in result["reason"]

    def test_tailwind_team_with_all_fast_scores_one(self):
        r = _report(roles={**_report()["roles"], "tailwind_setter": 1, "trick_room_setter": 0})
        builds = [_build(speed=TAILWIND_SPEED_THRESHOLD + 50)] * 6
        result = compute_speed_control_score(r, builds)
        assert result["score"] == pytest.approx(1.0)
        assert "Tailwind" in result["reason"]

    def test_tailwind_team_with_no_fast_scores_half(self):
        r = _report(roles={**_report()["roles"], "tailwind_setter": 1, "trick_room_setter": 0})
        builds = [_build(speed=TAILWIND_SPEED_THRESHOLD - 50)] * 6
        result = compute_speed_control_score(r, builds)
        assert result["score"] == pytest.approx(0.5)

    def test_tr_team_with_all_slow_scores_one(self):
        r = _report(roles={**_report()["roles"], "tailwind_setter": 0, "trick_room_setter": 1})
        builds = [_build(speed=TR_SPEED_THRESHOLD - 10)] * 6
        result = compute_speed_control_score(r, builds)
        assert result["score"] == pytest.approx(1.0)
        assert "Trick Room" in result["reason"]

    def test_tr_team_with_no_slow_scores_half(self):
        r = _report(roles={**_report()["roles"], "tailwind_setter": 0, "trick_room_setter": 1})
        builds = [_build(speed=TR_SPEED_THRESHOLD + 50)] * 6
        result = compute_speed_control_score(r, builds)
        assert result["score"] == pytest.approx(0.5)

    def test_returns_score_and_reason_keys(self):
        r = _report()
        result = compute_speed_control_score(r, [_build()] * 6)
        assert "score" in result
        assert "reason" in result


# ---------------------------------------------------------------------------
# compute_lead_pair_score
# ---------------------------------------------------------------------------

class TestLeadPairScore:
    def test_no_viable_pair_scores_zero(self):
        # 6 tanks — no disruption, no attacker with disruption partner
        builds = [_build()] * 6  # no roles that form viable pairs
        result = compute_lead_pair_score(builds)
        assert result["score"] == 0.0
        assert "no viable lead pair" in result["reason"]

    def test_one_viable_pair_scores_point_six(self):
        # fake_out_user + physical_attacker = 1 viable pair
        # Use real builds that detect_roles can classify
        disruptor = _build(move_names=("fake-out",))
        attacker = _build(speed=310, attack=350,
                          move_names=("tackle", "tackle", "tackle"))
        # Fill remaining with neutral builds
        filler = [_build()] * 4
        builds = [disruptor, attacker] + filler
        result = compute_lead_pair_score(builds)
        assert result["score"] == pytest.approx(0.6)
        assert "1 viable lead pair" in result["reason"]

    def test_three_or_more_viable_pairs_scores_one(self):
        disruptor1 = _build(move_names=("fake-out",))
        disruptor2 = _build(move_names=("follow-me",))
        attacker1 = _build(speed=310, attack=350, move_names=("tackle", "tackle", "tackle"))
        attacker2 = _build(speed=310, sp_attack=350, move_names=("flamethrower", "flamethrower", "flamethrower"))
        setter = _build(move_names=("tailwind",))
        filler = _build()
        builds = [disruptor1, disruptor2, attacker1, attacker2, setter, filler]
        result = compute_lead_pair_score(builds)
        assert result["score"] == pytest.approx(1.0)
        assert "viable lead pair" in result["reason"]

    def test_returns_score_and_reason(self):
        result = compute_lead_pair_score([_build()] * 6)
        assert "score" in result
        assert "reason" in result


# ---------------------------------------------------------------------------
# score_team
# ---------------------------------------------------------------------------

class TestScoreTeam:
    def test_returns_score_in_0_to_10_range(self):
        result = score_team(_report(), [_build()] * 6)
        assert 0.0 <= result["score"] <= 10.0

    def test_breakdown_has_speed_control_key(self):
        result = score_team(_report(), [_build()] * 6)
        assert "speed_control" in result["breakdown"]

    def test_breakdown_has_lead_pair_key(self):
        result = score_team(_report(), [_build()] * 6)
        assert "lead_pair" in result["breakdown"]

    def test_breakdown_does_not_have_old_speed_key(self):
        result = score_team(_report(), [_build()] * 6)
        assert "speed" not in result["breakdown"]

    def test_weights_has_speed_control_key(self):
        assert "speed_control" in WEIGHTS

    def test_weights_has_lead_pair_key(self):
        assert "lead_pair" in WEIGHTS

    def test_weights_does_not_have_speed_key(self):
        assert "speed" not in WEIGHTS

    def test_good_team_outscores_bad_team(self):
        good_builds = [
            _build(speed=310, attack=350, move_names=("tackle", "tackle", "tackle")),
            _build(speed=310, sp_attack=350, move_names=("flamethrower", "flamethrower")),
            _build(move_names=("tailwind",)),
            _build(move_names=("fake-out",)),
            _build(move_names=("earthquake",)),
            _build(speed=200),
        ]
        good_report = _report()
        bad_builds = [_build()] * 6
        bad_report = _report(
            weaknesses={"ground": 5, "fire": 4},
            roles={**_report()["roles"], "speed_control": 0, "disruption": 0},
            issues=["Missing speed control (need ≥ 1)", "Missing disruption (need ≥ 1)"],
            valid=False,
        )
        good_score = score_team(good_report, good_builds)["score"]
        bad_score = score_team(bad_report, bad_builds)["score"]
        assert good_score > bad_score
