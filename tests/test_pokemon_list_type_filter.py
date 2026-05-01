"""Tests for type filter on GET /pokemon/."""

import pytest
from fastapi.testclient import TestClient
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from src.api.main import app

_GARCHOMP_ROW  = (445, 'garchomp',  4, 108, 130, 95,  80,  85, 102)
_FERROTHORN_ROW = (598, 'ferrothorn', 5,  74,  94, 131, 54, 116,  20)
_GARCHOMP_TYPES  = [(445, 16, 'dragon'), (445, 5, 'ground')]
_FERROTHORN_TYPES = [(598, 12, 'grass'),  (598, 9, 'steel')]


def _make_cursor(count, pokemon_rows, type_rows):
    m = MagicMock()
    m.fetchone.return_value = (count,)
    m.fetchall.side_effect = [pokemon_rows, type_rows]
    return m


@contextmanager
def _ctx(cursor):
    yield cursor


class TestListPokemonTypeFilter:
    def test_type_filter_returns_matching_items(self):
        cursor = _make_cursor(1, [_GARCHOMP_ROW], _GARCHOMP_TYPES)
        with patch("src.api.routes.pokemon.get_db_cursor", lambda: _ctx(cursor)):
            with TestClient(app) as client:
                res = client.get("/pokemon/?type=dragon")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["items"][0]["name"] == "garchomp"
        assert any(t["type_name"] == "dragon" for t in data["items"][0]["types"])

    def test_type_filter_combined_with_name(self):
        cursor = _make_cursor(1, [_GARCHOMP_ROW], _GARCHOMP_TYPES)
        with patch("src.api.routes.pokemon.get_db_cursor", lambda: _ctx(cursor)):
            with TestClient(app) as client:
                res = client.get("/pokemon/?type=dragon&name=garchomp")
        assert res.status_code == 200
        assert res.json()["items"][0]["name"] == "garchomp"

    def test_unknown_type_returns_empty_list(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (0,)
        cursor.fetchall.return_value = []
        with patch("src.api.routes.pokemon.get_db_cursor", lambda: _ctx(cursor)):
            with TestClient(app) as client:
                res = client.get("/pokemon/?type=faketype")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_unfiltered_list_items_include_types_field(self):
        cursor = _make_cursor(1, [_GARCHOMP_ROW], _GARCHOMP_TYPES)
        with patch("src.api.routes.pokemon.get_db_cursor", lambda: _ctx(cursor)):
            with TestClient(app) as client:
                res = client.get("/pokemon/")
        assert res.status_code == 200
        item = res.json()["items"][0]
        assert "types" in item
        assert isinstance(item["types"], list)
        assert item["types"][0]["type_name"] == "dragon"
