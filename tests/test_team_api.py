# tests/test_team_api.py
"""API integration tests for POST /team/analyze."""

import pytest
from contextlib import contextmanager
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from src.api.main import app
from src.api.models.team import PokemonBuild, MoveDetail

BASE_STATS = {"hp": 357, "attack": 390, "defense": 226,
              "sp_attack": 176, "sp_defense": 210, "speed": 333}

FAKE_TEAM = [
    PokemonBuild("garchomp",   1, ["dragon", "ground"], "jolly", "rough-skin",
                 "Choice Scarf", BASE_STATS,
                 [MoveDetail("earthquake", "ground", "physical"),
                  MoveDetail("outrage",    "dragon", "physical"),
                  MoveDetail("stone-edge", "rock",   "physical"),
                  MoveDetail("fire-fang",  "fire",   "physical")]),
    PokemonBuild("ferrothorn", 2, ["grass", "steel"],  "relaxed", "iron-barbs",
                 "Leftovers", BASE_STATS,
                 [MoveDetail("stealth-rock", "rock",  "status"),
                  MoveDetail("power-whip",   "grass", "physical"),
                  MoveDetail("leech-seed",   "grass", "status"),
                  MoveDetail("knock-off",    "dark",  "physical")]),
    PokemonBuild("blissey",    3, ["normal"],          "bold",    "natural-cure",
                 "Leftovers", BASE_STATS,
                 [MoveDetail("soft-boiled",  "normal", "status"),
                  MoveDetail("wish",         "normal", "status"),
                  MoveDetail("seismic-toss", "normal", "physical"),
                  MoveDetail("thunder-wave", "electric", "status")]),
    PokemonBuild("rotom-wash", 4, ["electric", "water"], "bold", "levitate",
                 "Rocky Helmet", BASE_STATS,
                 [MoveDetail("volt-switch",  "electric", "special"),
                  MoveDetail("hydro-pump",   "water",    "special"),
                  MoveDetail("will-o-wisp",  "fire",     "status"),
                  MoveDetail("pain-split",   "normal",   "status")]),
    PokemonBuild("clefable",   5, ["fairy"],           "calm",    "magic-guard",
                 "Leftovers", BASE_STATS,
                 [MoveDetail("moonblast",    "fairy",  "special"),
                  MoveDetail("flamethrower", "fire",   "special"),
                  MoveDetail("soft-boiled",  "normal", "status"),
                  MoveDetail("calm-mind",    "psychic","status")]),
    PokemonBuild("landorus-therian", 6, ["ground", "flying"], "jolly",
                 "choice-scarf", "Choice Scarf", BASE_STATS,
                 [MoveDetail("earthquake",   "ground", "physical"),
                  MoveDetail("u-turn",       "bug",    "physical"),
                  MoveDetail("stone-edge",   "rock",   "physical"),
                  MoveDetail("knock-off",    "dark",   "physical")]),
]

FAKE_ANALYSIS = {
    "valid": True,
    "issues": [],
    "roles": {"physical_sweeper": 2, "special_sweeper": 1, "tank": 1,
              "hazard_setter": 1, "hazard_removal": 0, "pivot": 1, "support": 1},
    "weaknesses": {"ice": 3},
    "resistances": {"electric": 2},
    "coverage": {"covered_types": ["grass", "steel"], "missing_types": ["water"]},
}

VALID_PAYLOAD = [
    {"pokemon_name": "garchomp",         "set_id": 1},
    {"pokemon_name": "ferrothorn",       "set_id": 2},
    {"pokemon_name": "blissey",          "set_id": 3},
    {"pokemon_name": "rotom-wash",       "set_id": 4},
    {"pokemon_name": "clefable",         "set_id": 5},
    {"pokemon_name": "landorus-therian", "set_id": 6},
]


@contextmanager
def _mock_db():
    yield MagicMock()


@pytest.fixture
def client():
    with patch("src.api.routes.team.get_db_connection", _mock_db):
        with patch("src.api.routes.team.load_team",    return_value=FAKE_TEAM):
            with patch("src.api.routes.team.analyze_team", return_value=FAKE_ANALYSIS):
                with TestClient(app) as c:
                    yield c


@pytest.fixture
def client_not_found():
    with patch("src.api.routes.team.get_db_connection", _mock_db):
        with patch("src.api.routes.team.load_team",
                   side_effect=ValueError("Set 999 not found for Pokémon 'fakemon'")):
            with TestClient(app) as c:
                yield c


class TestTeamAnalyzeEndpoint:

    def test_returns_200(self, client):
        response = client.post("/team/analyze", json=VALID_PAYLOAD)
        assert response.status_code == 200

    def test_response_has_valid_key(self, client):
        data = client.post("/team/analyze", json=VALID_PAYLOAD).json()
        assert "valid" in data

    def test_response_has_issues_list(self, client):
        data = client.post("/team/analyze", json=VALID_PAYLOAD).json()
        assert isinstance(data["issues"], list)

    def test_response_has_roles_dict(self, client):
        data = client.post("/team/analyze", json=VALID_PAYLOAD).json()
        assert isinstance(data["roles"], dict)

    def test_response_has_weaknesses(self, client):
        data = client.post("/team/analyze", json=VALID_PAYLOAD).json()
        assert "weaknesses" in data

    def test_response_has_resistances(self, client):
        data = client.post("/team/analyze", json=VALID_PAYLOAD).json()
        assert "resistances" in data

    def test_response_has_coverage(self, client):
        data = client.post("/team/analyze", json=VALID_PAYLOAD).json()
        assert "coverage" in data
        assert "covered_types" in data["coverage"]
        assert "missing_types" in data["coverage"]

    def test_too_few_members_returns_422(self, client):
        response = client.post("/team/analyze", json=VALID_PAYLOAD[:3])
        assert response.status_code == 422

    def test_too_many_members_returns_422(self, client):
        response = client.post("/team/analyze", json=VALID_PAYLOAD + VALID_PAYLOAD[:1])
        assert response.status_code == 422

    def test_unknown_set_returns_404(self, client_not_found):
        response = client_not_found.post("/team/analyze", json=VALID_PAYLOAD)
        assert response.status_code == 404

    def test_empty_payload_returns_422(self, client):
        response = client.post("/team/analyze", json=[])
        assert response.status_code == 422
