# tests/test_meta_service.py
"""Unit tests for meta_service — all DB interactions are mocked."""

from unittest.mock import MagicMock, patch

import pytest


def _make_conn(fetchone_values=None, fetchall_values=None):
    cursor = MagicMock()
    cursor.__enter__ = MagicMock(return_value=cursor)
    cursor.__exit__ = MagicMock(return_value=False)
    if fetchone_values is not None:
        cursor.fetchone.side_effect = fetchone_values
    if fetchall_values is not None:
        cursor.fetchall.side_effect = fetchall_values
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


class TestGetMetaSnapshot:
    def test_returns_empty_when_no_battles(self):
        from src.api.services.meta_service import get_meta_snapshot
        conn, cursor = _make_conn(fetchone_values=[(0,)], fetchall_values=[[]])
        result = get_meta_snapshot(conn, regulation_id=1)
        assert result["total_battles"] == 0
        assert result["top_pokemon"] == []

    def test_returns_top_pokemon_with_usage_pct(self):
        from src.api.services.meta_service import get_meta_snapshot
        conn, cursor = _make_conn(
            fetchone_values=[(100,)],
            fetchall_values=[[("koraidon", 80), ("miraidon", 60)]],
        )
        result = get_meta_snapshot(conn, regulation_id=1, top_n=2)
        assert result["total_battles"] == 100
        assert result["top_pokemon"][0]["name"] == "koraidon"
        assert result["top_pokemon"][0]["usage_pct"] == round(80 / 200, 3)

    def test_usage_pct_denominator_is_total_times_two(self):
        from src.api.services.meta_service import get_meta_snapshot
        conn, cursor = _make_conn(
            fetchone_values=[(10,)],
            fetchall_values=[[("koraidon", 10)]],
        )
        result = get_meta_snapshot(conn, regulation_id=1)
        assert result["top_pokemon"][0]["usage_pct"] == 0.5


class TestGetBattleMatchups:
    def test_returns_winner_loser_pairs(self):
        from src.api.services.meta_service import get_battle_matchups
        conn, cursor = _make_conn(
            fetchall_values=[[
                (["koraidon", "incineroar"], ["miraidon", "amoonguss"]),
                (["miraidon", "iron-hands"], ["koraidon", "flutter-mane"]),
            ]]
        )
        result = get_battle_matchups(conn, regulation_id=1)
        assert len(result) == 2
        assert result[0]["winner"] == ["koraidon", "incineroar"]
        assert result[0]["loser"] == ["miraidon", "amoonguss"]

    def test_returns_empty_list_when_no_data(self):
        from src.api.services.meta_service import get_battle_matchups
        conn, cursor = _make_conn(fetchall_values=[[]])
        result = get_battle_matchups(conn, regulation_id=1)
        assert result == []


class TestComputeWinRates:
    def test_returns_empty_when_no_meta_matchups(self):
        from src.api.services.meta_service import compute_win_rates
        matchups = [{"winner": ["koraidon"], "loser": ["urshifu"]}]
        result = compute_win_rates(matchups, meta_pokemon={"miraidon"})
        assert result == {}

    def test_pokemon_with_all_wins_has_rate_one(self):
        from src.api.services.meta_service import compute_win_rates
        matchups = [
            {"winner": ["koraidon"], "loser": ["miraidon"]},
            {"winner": ["koraidon"], "loser": ["miraidon"]},
        ]
        rates = compute_win_rates(matchups, meta_pokemon={"miraidon"})
        assert rates["koraidon"] == 1.0

    def test_pokemon_with_all_losses_has_rate_zero(self):
        from src.api.services.meta_service import compute_win_rates
        matchups = [{"winner": ["miraidon"], "loser": ["koraidon"]}]
        rates = compute_win_rates(matchups, meta_pokemon={"koraidon"})
        assert rates.get("miraidon", 1.0) != 0.0
        assert rates.get("koraidon", 0.0) == pytest.approx(0.0)

    def test_fifty_fifty_rate(self):
        from src.api.services.meta_service import compute_win_rates
        matchups = [
            {"winner": ["koraidon"], "loser": ["miraidon"]},
            {"winner": ["miraidon"], "loser": ["koraidon"]},
        ]
        rates = compute_win_rates(matchups, meta_pokemon={"miraidon", "koraidon"})
        assert rates["koraidon"] == pytest.approx(0.5)
        assert rates["miraidon"] == pytest.approx(0.5)
