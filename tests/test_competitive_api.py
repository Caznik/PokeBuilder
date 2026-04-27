# tests/test_competitive_api.py
"""API integration tests for GET /competitive-sets/{pokemon_name}."""

import pytest
from contextlib import contextmanager
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app


@contextmanager
def _mock_cursor():
    yield MagicMock()

GARCHOMP_SETS = [
    {
        "id": 1,
        "name": "Choice Scarf",
        "nature": "jolly",
        "ability": "rough-skin",
        "item": "Choice Scarf",
        "evs": {"hp": 0, "attack": 252, "defense": 0, "sp_attack": 0, "sp_defense": 4, "speed": 252},
        "moves": ["earthquake", "outrage", "stone-edge", "fire-fang"],
    }
]


@pytest.fixture
def client():
    with patch("src.api.routes.competitive.get_db_cursor", _mock_cursor):
        with patch("src.api.routes.competitive.get_sets_for_pokemon", return_value=GARCHOMP_SETS):
            with TestClient(app) as c:
                yield c


@pytest.fixture
def client_no_sets():
    with patch("src.api.routes.competitive.get_db_cursor", _mock_cursor):
        with patch("src.api.routes.competitive.get_sets_for_pokemon", return_value=[]):
            with TestClient(app) as c:
                yield c


@pytest.fixture
def client_not_found():
    with patch("src.api.routes.competitive.get_db_cursor", _mock_cursor):
        with patch(
            "src.api.routes.competitive.get_sets_for_pokemon",
            side_effect=ValueError("Pokemon 'fakemon' not found"),
        ):
            with TestClient(app) as c:
                yield c


class TestGetCompetitiveSets:

    def test_returns_200_with_sets(self, client):
        response = client.get("/competitive-sets/garchomp")
        assert response.status_code == 200

    def test_response_contains_pokemon_name(self, client):
        data = client.get("/competitive-sets/garchomp").json()
        assert data["pokemon"] == "garchomp"

    def test_response_contains_sets_list(self, client):
        data = client.get("/competitive-sets/garchomp").json()
        assert "sets" in data
        assert isinstance(data["sets"], list)
        assert len(data["sets"]) == 1

    def test_set_has_required_fields(self, client):
        s = client.get("/competitive-sets/garchomp").json()["sets"][0]
        for field in ("id", "name", "nature", "ability", "item", "evs", "moves"):
            assert field in s, f"Missing field: {field}"

    def test_evs_has_all_stats(self, client):
        evs = client.get("/competitive-sets/garchomp").json()["sets"][0]["evs"]
        for stat in ("hp", "attack", "defense", "sp_attack", "sp_defense", "speed"):
            assert stat in evs

    def test_moves_is_list_of_strings(self, client):
        moves = client.get("/competitive-sets/garchomp").json()["sets"][0]["moves"]
        assert isinstance(moves, list)
        for m in moves:
            assert isinstance(m, str)

    def test_returns_200_with_empty_sets_when_none_ingested(self, client_no_sets):
        data = client_no_sets.get("/competitive-sets/magikarp").json()
        assert data["sets"] == []

    def test_returns_404_for_unknown_pokemon(self, client_not_found):
        response = client_not_found.get("/competitive-sets/fakemon")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_case_insensitive_url(self, client):
        """Route should accept mixed-case names."""
        response = client.get("/competitive-sets/Garchomp")
        assert response.status_code == 200

    def test_ev_values_are_integers(self, client):
        evs = client.get("/competitive-sets/garchomp").json()["sets"][0]["evs"]
        for val in evs.values():
            assert isinstance(val, int)
