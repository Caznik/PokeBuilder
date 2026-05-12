"""API integration tests for /battle-logs endpoints."""

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models.auth import UserOut
from src.api.models.battle_log import BattleLogOut
from src.api.services.auth_service import get_current_user

_AUTH_USER = UserOut(id=1, email="test@example.com")
_NOW = datetime(2026, 5, 12, 10, 0, 0, tzinfo=timezone.utc)

_LOG_OUT = BattleLogOut(
    id=1,
    user_id=1,
    saved_team_id=None,
    saved_team_name=None,
    regulation_id=None,
    format="singles",
    brought_pokemon=["charizard", "blastoise", "venusaur"],
    enemy_team=["pikachu", "mewtwo"],
    enemy_brought=[],
    result="win",
    notes=None,
    played_at=_NOW,
    saved_team_members=[],
)

_VALID_CREATE_PAYLOAD = {
    "format": "singles",
    "brought_pokemon": ["charizard", "blastoise", "venusaur"],
    "enemy_team": ["pikachu", "mewtwo"],
    "result": "win",
}


def _override_auth():
    return _AUTH_USER


@pytest.fixture(autouse=True)
def _apply_auth_override():
    """Inject auth user for every test in this module."""
    app.dependency_overrides[get_current_user] = _override_auth
    yield
    app.dependency_overrides.pop(get_current_user, None)


client = TestClient(app)


@contextmanager
def _mock_db():
    yield MagicMock()


class TestCreateEndpoint:
    def test_valid_post_returns_201(self):
        with (
            patch("src.api.routes.battle_logs.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.battle_logs.create_log", return_value=_LOG_OUT),
        ):
            resp = client.post("/battle-logs/", json=_VALID_CREATE_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["id"] == 1

    def test_invalid_brought_pokemon_count_returns_422(self):
        """Singles with 2 brought_pokemon (need 3) → 422."""
        bad = {**_VALID_CREATE_PAYLOAD, "brought_pokemon": ["charizard", "blastoise"]}
        resp = client.post("/battle-logs/", json=bad)
        assert resp.status_code == 422

    def test_empty_enemy_team_returns_422(self):
        """enemy_team with 0 entries → 422."""
        bad = {**_VALID_CREATE_PAYLOAD, "enemy_team": []}
        resp = client.post("/battle-logs/", json=bad)
        assert resp.status_code == 422

    def test_enemy_team_too_large_returns_422(self):
        """enemy_team with 7 entries → 422."""
        bad = {**_VALID_CREATE_PAYLOAD, "enemy_team": [f"p{i}" for i in range(7)]}
        resp = client.post("/battle-logs/", json=bad)
        assert resp.status_code == 422

    def test_vgc_requires_4_brought(self):
        """VGC with 3 brought_pokemon → 422."""
        bad = {
            "format": "vgc",
            "brought_pokemon": ["a", "b", "c"],
            "enemy_team": ["x"],
            "result": "win",
        }
        resp = client.post("/battle-logs/", json=bad)
        assert resp.status_code == 422


class TestListEndpoint:
    def test_returns_200_and_list(self):
        with (
            patch("src.api.routes.battle_logs.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.battle_logs.list_logs", return_value=[_LOG_OUT]),
        ):
            resp = client.get("/battle-logs/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) == 1

    def test_returns_empty_list(self):
        with (
            patch("src.api.routes.battle_logs.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.battle_logs.list_logs", return_value=[]),
        ):
            resp = client.get("/battle-logs/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_regulation_id_filter_forwarded_to_service(self):
        with (
            patch("src.api.routes.battle_logs.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.battle_logs.list_logs", return_value=[]) as mock_list,
        ):
            resp = client.get("/battle-logs/?regulation_id=3")
        assert resp.status_code == 200
        _, kwargs = mock_list.call_args
        assert kwargs.get("regulation_id") == 3

    def test_format_filter_forwarded_to_service(self):
        with (
            patch("src.api.routes.battle_logs.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.battle_logs.list_logs", return_value=[]) as mock_list,
        ):
            resp = client.get("/battle-logs/?format=singles")
        assert resp.status_code == 200
        _, kwargs = mock_list.call_args
        assert kwargs.get("format") == "singles"

    def test_result_filter_forwarded_to_service(self):
        with (
            patch("src.api.routes.battle_logs.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.battle_logs.list_logs", return_value=[]) as mock_list,
        ):
            resp = client.get("/battle-logs/?result=win")
        assert resp.status_code == 200
        _, kwargs = mock_list.call_args
        assert kwargs.get("result") == "win"


class TestGetEndpoint:
    def test_found_returns_200(self):
        with (
            patch("src.api.routes.battle_logs.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.battle_logs.get_log", return_value=_LOG_OUT),
        ):
            resp = client.get("/battle-logs/1")
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    def test_not_found_returns_404(self):
        with (
            patch("src.api.routes.battle_logs.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.battle_logs.get_log", side_effect=ValueError("not found")),
        ):
            resp = client.get("/battle-logs/999")
        assert resp.status_code == 404


class TestDeleteEndpoint:
    def test_success_returns_204(self):
        with (
            patch("src.api.routes.battle_logs.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.battle_logs.delete_log", return_value=None),
        ):
            resp = client.delete("/battle-logs/1")
        assert resp.status_code == 204

    def test_not_found_returns_404(self):
        with (
            patch("src.api.routes.battle_logs.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.battle_logs.delete_log", side_effect=ValueError("not found")),
        ):
            resp = client.delete("/battle-logs/999")
        assert resp.status_code == 404
