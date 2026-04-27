# tests/test_competitive_service.py
"""Unit tests for competitive_service with synthetic DB data."""

import pytest
from unittest.mock import MagicMock

from src.api.services.competitive_service import get_sets_for_pokemon


def _make_cursor(pokemon_row, set_rows, move_rows_per_set: dict):
    """Build a mock cursor with pre-programmed fetchone/fetchall sequences."""
    cursor = MagicMock()
    call_count = {"n": 0}

    def execute(sql, params=None):
        call_count["n"] += 1
        cursor._last_sql = sql

    def fetchone():
        sql = cursor._last_sql
        if "FROM pokemon" in sql:
            return pokemon_row
        return None

    def fetchall():
        sql = cursor._last_sql
        if "FROM competitive_sets" in sql:
            return set_rows
        # move query — use set_id from last params
        set_id = cursor._last_params[0] if hasattr(cursor, "_last_params") else None
        return move_rows_per_set.get(set_id, [])

    # Track params too
    original_execute = execute

    def execute_with_params(sql, params=None):
        original_execute(sql, params)
        cursor._last_params = params

    cursor.execute.side_effect = execute_with_params
    cursor.fetchone.side_effect = fetchone
    cursor.fetchall.side_effect = fetchall
    return cursor


class TestGetSetsForPokemon:

    def test_returns_sets_for_known_pokemon(self):
        """Should return structured set list for a Pokémon with sets."""
        cursor = MagicMock()
        # pokemon lookup
        cursor.fetchone.side_effect = [(1,)]
        # sets query
        cursor.fetchall.side_effect = [
            # set rows: (id, name, nature, ability, item, hp, atk, def, spa, spd, spe)
            [(10, "Offensive", "jolly", "rough-skin", "Choice Scarf", 0, 252, 0, 0, 4, 252)],
            # moves for set 10
            [("earthquake",), ("dragon-claw",), ("stone-edge",), ("fire-fang",)],
        ]

        result = get_sets_for_pokemon(cursor, "garchomp")

        assert len(result) == 1
        s = result[0]
        assert s["id"] == 10
        assert s["name"] == "Offensive"
        assert s["nature"] == "jolly"
        assert s["ability"] == "rough-skin"
        assert s["item"] == "Choice Scarf"
        assert s["evs"]["attack"] == 252
        assert s["evs"]["speed"] == 252
        assert s["moves"] == ["earthquake", "dragon-claw", "stone-edge", "fire-fang"]

    def test_returns_empty_sets_when_none_ingested(self):
        """Should return empty list when Pokémon exists but has no sets."""
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(42,)]  # pokemon exists
        cursor.fetchall.side_effect = [[]]    # no sets

        result = get_sets_for_pokemon(cursor, "magikarp")

        assert result == []

    def test_raises_value_error_for_unknown_pokemon(self):
        """Should raise ValueError when Pokémon is not in the DB."""
        cursor = MagicMock()
        cursor.fetchone.return_value = None  # not found

        with pytest.raises(ValueError, match="not found"):
            get_sets_for_pokemon(cursor, "fakemon")

    def test_case_insensitive_name(self):
        """Lookup should be case-insensitive (SQL uses LOWER())."""
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(1,)]
        cursor.fetchall.side_effect = [[], ]

        # Should not raise
        result = get_sets_for_pokemon(cursor, "GARCHOMP")
        assert isinstance(result, list)

    def test_multiple_sets_returned(self):
        """Should return all sets, not just the first."""
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(1,)]
        cursor.fetchall.side_effect = [
            [
                (10, "Choice Scarf", "jolly", "rough-skin", "Choice Scarf", 0, 252, 0, 0, 4, 252),
                (11, "Defensive", "impish", "rough-skin", "Rocky Helmet",  252, 0, 252, 0, 4, 0),
            ],
            [("earthquake",)],   # moves for set 10
            [("stealth-rock",)], # moves for set 11
        ]

        result = get_sets_for_pokemon(cursor, "garchomp")

        assert len(result) == 2
        assert result[0]["name"] == "Choice Scarf"
        assert result[1]["name"] == "Defensive"

    def test_set_with_null_fields(self):
        """Sets with NULL nature/ability/item should return None gracefully."""
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(1,)]
        cursor.fetchall.side_effect = [
            [(10, None, None, None, None, 0, 0, 0, 0, 0, 0)],
            [],
        ]

        result = get_sets_for_pokemon(cursor, "garchomp")

        assert result[0]["nature"] is None
        assert result[0]["ability"] is None
        assert result[0]["item"] is None
        assert result[0]["moves"] == []
