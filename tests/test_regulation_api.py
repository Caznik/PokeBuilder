# tests/test_regulation_api.py
"""API integration tests for /regulations endpoints."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

_REG_LIST = [
    {"id": 1, "name": "Reg E", "description": "Example regulation"},
    {"id": 2, "name": "Reg F", "description": None},
]

_REG_DETAIL = {
    "id": 1,
    "name": "Reg E",
    "description": "Example regulation",
    "pokemon": ["bulbasaur", "charmander"],
}


@contextmanager
def _mock_cursor():
    yield MagicMock()


def _patch_cursor():
    return patch("src.api.routes.regulation.get_db_cursor", _mock_cursor)


# ---------------------------------------------------------------------------
# GET /regulations/
# ---------------------------------------------------------------------------

class TestListRegulations:
    def test_returns_200(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.list_regulations",
                       return_value=_REG_LIST):
                resp = client.get("/regulations/")
        assert resp.status_code == 200

    def test_response_is_list(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.list_regulations",
                       return_value=_REG_LIST):
                resp = client.get("/regulations/")
        assert isinstance(resp.json(), list)

    def test_items_have_id_name_description(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.list_regulations",
                       return_value=_REG_LIST):
                resp = client.get("/regulations/")
        for item in resp.json():
            assert "id" in item
            assert "name" in item
            assert "description" in item

    def test_empty_list_returns_200(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.list_regulations",
                       return_value=[]):
                resp = client.get("/regulations/")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /regulations/
# ---------------------------------------------------------------------------

class TestCreateRegulation:
    def test_returns_201_on_success(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.create_regulation",
                       return_value=_REG_DETAIL):
                resp = client.post("/regulations/", json={
                    "name": "Reg E",
                    "description": "Example regulation",
                    "pokemon_names": ["bulbasaur"],
                })
        assert resp.status_code == 201

    def test_response_has_pokemon_list(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.create_regulation",
                       return_value=_REG_DETAIL):
                resp = client.post("/regulations/", json={
                    "name": "Reg E",
                    "pokemon_names": ["bulbasaur"],
                })
        assert "pokemon" in resp.json()

    def test_unknown_pokemon_returns_400(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.create_regulation",
                       side_effect=ValueError("unknown Pokémon names: fakemon")):
                resp = client.post("/regulations/", json={
                    "name": "Reg E",
                    "pokemon_names": ["fakemon"],
                })
        assert resp.status_code == 400

    def test_duplicate_name_returns_409(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.create_regulation",
                       side_effect=ValueError("regulation 'Reg E' already exists")):
                resp = client.post("/regulations/", json={
                    "name": "Reg E",
                    "pokemon_names": ["bulbasaur"],
                })
        assert resp.status_code == 409

    def test_missing_pokemon_names_returns_422(self):
        resp = client.post("/regulations/", json={"name": "Reg E"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /regulations/{id}
# ---------------------------------------------------------------------------

class TestGetRegulation:
    def test_returns_200_with_pokemon(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.get_regulation",
                       return_value=_REG_DETAIL):
                resp = client.get("/regulations/1")
        assert resp.status_code == 200
        assert resp.json()["pokemon"] == ["bulbasaur", "charmander"]

    def test_returns_404_for_missing(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.get_regulation",
                       side_effect=ValueError("regulation 999 not found")):
                resp = client.get("/regulations/999")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /regulations/{id}
# ---------------------------------------------------------------------------

class TestUpdateRegulation:
    def test_returns_200_on_success(self):
        updated = {**_REG_DETAIL, "name": "Reg E Updated"}
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.update_regulation",
                       return_value=updated):
                resp = client.patch("/regulations/1", json={"name": "Reg E Updated"})
        assert resp.status_code == 200

    def test_returns_404_for_missing(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.update_regulation",
                       side_effect=ValueError("regulation 999 not found")):
                resp = client.patch("/regulations/999", json={"name": "X"})
        assert resp.status_code == 404

    def test_unknown_pokemon_in_patch_returns_400(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.update_regulation",
                       side_effect=ValueError("unknown Pokémon names: fakemon")):
                resp = client.patch("/regulations/1", json={"pokemon_names": ["fakemon"]})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /regulations/{id}
# ---------------------------------------------------------------------------

class TestDeleteRegulation:
    def test_returns_204_on_success(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.delete_regulation"):
                resp = client.delete("/regulations/1")
        assert resp.status_code == 204

    def test_returns_404_for_missing(self):
        with _patch_cursor():
            with patch("src.api.routes.regulation.regulation_service.delete_regulation",
                       side_effect=ValueError("regulation 999 not found")):
                resp = client.delete("/regulations/999")
        assert resp.status_code == 404
