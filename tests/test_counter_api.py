# tests/test_counter_api.py
"""Unit tests for the /team/counter endpoint."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestCounterEndpoint:
    def test_returns_400_when_insufficient_data(self):
        with (
            patch("src.api.routes.counter.get_db_connection"),
            patch("src.api.routes.counter.suggest_counter_team",
                  side_effect=ValueError("Not enough battle data")),
        ):
            resp = client.post("/team/counter", json={"regulation_id": 1})
        assert resp.status_code == 400
        assert "Not enough battle data" in resp.json()["detail"]

    def test_returns_200_with_valid_result(self):
        mock_result = {
            "best_teams": [],
            "algorithm": "beam_search",
            "meta_snapshot": {"top_pokemon": [], "total_battles": 50},
            "replays_analyzed": 50,
        }
        with (
            patch("src.api.routes.counter.get_db_connection"),
            patch("src.api.routes.counter.suggest_counter_team", return_value=mock_result),
        ):
            resp = client.post("/team/counter", json={"regulation_id": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert data["algorithm"] == "beam_search"
        assert data["replays_analyzed"] == 50
        assert "meta_snapshot" in data

    def test_validates_beam_width_maximum(self):
        resp = client.post("/team/counter", json={"regulation_id": 1, "beam_width": 999})
        assert resp.status_code == 422
