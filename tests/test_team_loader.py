# tests/test_team_loader.py
"""Unit tests for team_loader with mocked DB."""

import pytest
from unittest.mock import MagicMock, patch, call

from src.api.models.team import PokemonBuild, MoveDetail
from src.api.services.team_loader import load_build, load_team


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_conn(set_row=None, type_rows=None, move_rows=None):
    """Build a mock connection whose cursor returns preset rows."""
    cur = MagicMock()
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    # Each execute → fetchone / fetchall pair is consumed in order
    cur.fetchone.side_effect = [set_row]
    cur.fetchall.side_effect = [type_rows or [], move_rows or []]
    return conn, cur


SET_ROW = (
    1,              # set_id
    "Choice Scarf", # set_name
    "jolly",        # nature
    "rough-skin",   # ability
    "Choice Scarf", # item
    0, 252, 0, 0, 4, 252,  # hp atk def spa spd spe (EVs)
)

TYPE_ROWS = [("dragon",), ("ground",)]

MOVE_ROWS = [
    ("earthquake",  "ground",  "physical"),
    ("outrage",     "dragon",  "physical"),
    ("stone-edge",  "rock",    "physical"),
    ("fire-fang",   "fire",    "physical"),
]

COMPUTED_STATS = {
    "hp": 357, "attack": 390, "defense": 226,
    "sp_attack": 176, "sp_defense": 210, "speed": 333,
}


class TestLoadBuild:

    def test_returns_pokemon_build(self):
        conn, _ = _make_conn(SET_ROW, TYPE_ROWS, MOVE_ROWS)
        with patch("src.api.services.team_loader.calculate_stats", return_value=COMPUTED_STATS):
            build = load_build(conn, "garchomp", 1)
        assert isinstance(build, PokemonBuild)

    def test_pokemon_name_set(self):
        conn, _ = _make_conn(SET_ROW, TYPE_ROWS, MOVE_ROWS)
        with patch("src.api.services.team_loader.calculate_stats", return_value=COMPUTED_STATS):
            build = load_build(conn, "garchomp", 1)
        assert build.pokemon_name == "garchomp"

    def test_set_id_set(self):
        conn, _ = _make_conn(SET_ROW, TYPE_ROWS, MOVE_ROWS)
        with patch("src.api.services.team_loader.calculate_stats", return_value=COMPUTED_STATS):
            build = load_build(conn, "garchomp", 1)
        assert build.set_id == 1

    def test_types_loaded(self):
        conn, _ = _make_conn(SET_ROW, TYPE_ROWS, MOVE_ROWS)
        with patch("src.api.services.team_loader.calculate_stats", return_value=COMPUTED_STATS):
            build = load_build(conn, "garchomp", 1)
        assert build.types == ["dragon", "ground"]

    def test_nature_loaded(self):
        conn, _ = _make_conn(SET_ROW, TYPE_ROWS, MOVE_ROWS)
        with patch("src.api.services.team_loader.calculate_stats", return_value=COMPUTED_STATS):
            build = load_build(conn, "garchomp", 1)
        assert build.nature == "jolly"

    def test_ability_loaded(self):
        conn, _ = _make_conn(SET_ROW, TYPE_ROWS, MOVE_ROWS)
        with patch("src.api.services.team_loader.calculate_stats", return_value=COMPUTED_STATS):
            build = load_build(conn, "garchomp", 1)
        assert build.ability == "rough-skin"

    def test_item_loaded(self):
        conn, _ = _make_conn(SET_ROW, TYPE_ROWS, MOVE_ROWS)
        with patch("src.api.services.team_loader.calculate_stats", return_value=COMPUTED_STATS):
            build = load_build(conn, "garchomp", 1)
        assert build.item == "Choice Scarf"

    def test_stats_computed(self):
        conn, _ = _make_conn(SET_ROW, TYPE_ROWS, MOVE_ROWS)
        with patch("src.api.services.team_loader.calculate_stats", return_value=COMPUTED_STATS):
            build = load_build(conn, "garchomp", 1)
        assert build.stats == COMPUTED_STATS

    def test_moves_loaded_with_detail(self):
        conn, _ = _make_conn(SET_ROW, TYPE_ROWS, MOVE_ROWS)
        with patch("src.api.services.team_loader.calculate_stats", return_value=COMPUTED_STATS):
            build = load_build(conn, "garchomp", 1)
        assert len(build.moves) == 4
        assert build.moves[0] == MoveDetail("earthquake", "ground", "physical")

    def test_raises_if_set_not_found(self):
        conn, _ = _make_conn(set_row=None, type_rows=[], move_rows=[])
        with patch("src.api.services.team_loader.calculate_stats", return_value=COMPUTED_STATS):
            with pytest.raises(ValueError, match="not found"):
                load_build(conn, "garchomp", 999)


class TestLoadTeam:

    def test_returns_list_of_builds(self):
        members = [
            {"pokemon_name": "garchomp", "set_id": 1},
            {"pokemon_name": "ferrothorn", "set_id": 2},
        ]
        fake_build = PokemonBuild("garchomp", 1, ["dragon", "ground"], "jolly",
                                  "rough-skin", "Choice Scarf", COMPUTED_STATS, [])
        with patch("src.api.services.team_loader.load_build", return_value=fake_build):
            result = load_team(MagicMock(), members)
        assert len(result) == 2
        assert all(isinstance(b, PokemonBuild) for b in result)

    def test_calls_load_build_for_each_member(self):
        members = [{"pokemon_name": "garchomp", "set_id": 1}]
        fake_build = PokemonBuild("garchomp", 1, [], None, None, None, COMPUTED_STATS, [])
        with patch("src.api.services.team_loader.load_build", return_value=fake_build) as mock_lb:
            load_team(MagicMock(), members)
        mock_lb.assert_called_once()
