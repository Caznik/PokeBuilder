# tests/test_counter_optimizer.py
"""Unit tests for the beam-search counter optimizer."""

from unittest.mock import MagicMock, patch

import pytest

from src.api.services.team_generator import PoolEntry


def _pool(*names):
    return [PoolEntry(name, i + 1, f"{name}-set", "fire") for i, name in enumerate(names)]


class TestScorePartial:
    def test_zero_when_no_win_rate_data(self):
        from src.api.services.counter_optimizer import _score_partial
        partial = [("koraidon", 1), ("incineroar", 2)]
        assert _score_partial(partial, {}, frozenset(), 0) == 0.0

    def test_mean_of_member_win_rates(self):
        from src.api.services.counter_optimizer import _score_partial
        partial = [("koraidon", 1), ("incineroar", 2)]
        rates = {"koraidon": 0.8, "incineroar": 0.6}
        assert _score_partial(partial, rates, frozenset(), 0) == pytest.approx(0.7)

    def test_missing_pokemon_treated_as_zero(self):
        from src.api.services.counter_optimizer import _score_partial
        partial = [("koraidon", 1), ("unknown", 2)]
        rates = {"koraidon": 1.0}
        assert _score_partial(partial, rates, frozenset(), 0) == pytest.approx(0.5)

    def test_role_coverage_bonus_added(self):
        from src.api.services.counter_optimizer import _score_partial, _ROLE_COVERAGE_BONUS
        partial = [("incineroar", 1)]
        rates = {"incineroar": 0.6}
        covered = frozenset({"physical_attacker", "disruption"})
        expected = 0.6 + 2 * _ROLE_COVERAGE_BONUS
        assert _score_partial(partial, rates, covered, 0) == pytest.approx(expected)

    def test_type_diversity_bonus_added(self):
        from src.api.services.counter_optimizer import _score_partial, _TYPE_DIVERSITY_BONUS
        partial = [("koraidon", 1), ("incineroar", 2)]
        rates = {"koraidon": 0.6, "incineroar": 0.6}
        expected = 0.6 + 3 * _TYPE_DIVERSITY_BONUS  # 3 distinct types
        assert _score_partial(partial, rates, frozenset(), 3) == pytest.approx(expected)


class TestSuggestCounterTeam:
    def _setup_mocks(self, total_battles=50):
        meta_snapshot = {
            "top_pokemon": [{"name": "miraidon", "usage_pct": 0.4}],
            "total_battles": total_battles,
        }
        matchups = [
            {"winner": ["koraidon", "incineroar", "a", "b", "c", "d"],
             "loser": ["miraidon", "e", "f", "g", "h", "i"]}
            for _ in range(total_battles)
        ]
        return meta_snapshot, matchups

    def test_raises_when_insufficient_battle_data(self):
        from src.api.services.counter_optimizer import suggest_counter_team

        conn = MagicMock()
        with patch("src.api.services.counter_optimizer.get_meta_snapshot") as mock_meta:
            mock_meta.return_value = {"top_pokemon": [], "total_battles": 2}
            with pytest.raises(ValueError, match="Not enough battle data"):
                suggest_counter_team(conn, regulation_id=1)

    def test_returns_expected_keys(self):
        from src.api.services.counter_optimizer import suggest_counter_team

        pool = _pool("koraidon", "incineroar", "flutter-mane", "rillaboom", "urshifu", "farigiraf")
        meta_snapshot, matchups = self._setup_mocks()

        conn = MagicMock()
        with (
            patch("src.api.services.counter_optimizer.get_meta_snapshot", return_value=meta_snapshot),
            patch("src.api.services.counter_optimizer.get_battle_matchups", return_value=matchups),
            patch("src.api.services.counter_optimizer.regulation_service.get_regulation_info",
                  return_value=("Regulation M-A", {"koraidon", "incineroar", "flutter-mane",
                                                    "rillaboom", "urshifu", "farigiraf"})),
            patch("src.api.services.counter_optimizer._build_pool", return_value=pool),
            patch("src.api.services.counter_optimizer.load_build", return_value=MagicMock(nature="timid", ability="orichalcum-pulse")),
            patch("src.api.services.counter_optimizer.detect_roles",
                  return_value=["physical_attacker", "special_attacker", "speed_control", "disruption"]),
            patch("src.api.services.counter_optimizer.analyze_team", return_value={
                "valid": True, "issues": [], "roles": {}, "weaknesses": {},
                "resistances": {}, "coverage": {"covered_types": [], "missing_types": []},
                "speed_control_archetype": "none",
            }),
            patch("src.api.services.counter_optimizer.score_team", return_value={
                "score": 7.0,
                "breakdown": {
                    "coverage": {"score": 0.8, "reason": "ok"},
                    "defensive": {"score": 0.7, "reason": "ok"},
                    "role": {"score": 0.9, "reason": "ok"},
                    "speed_control": {"score": 0.6, "reason": "ok"},
                    "lead_pair": {"score": 0.8, "reason": "ok"},
                },
            }),
            patch("src.api.services.counter_optimizer._is_acceptable", return_value=True),
        ):
            result = suggest_counter_team(conn, regulation_id=1)

        assert "best_teams" in result
        assert result["algorithm"] == "beam_search"
        assert "meta_snapshot" in result
        assert "replays_analyzed" in result
