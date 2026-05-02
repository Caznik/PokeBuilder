# tests/test_optimization_api.py
"""API integration tests for POST /team/optimize."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

_BREAKDOWN = {
    "coverage":      {"score": 0.94, "reason": "missing fairy"},
    "defensive":     {"score": 1.00, "reason": "no shared weaknesses"},
    "role":          {"score": 1.00, "reason": "all role minimums met"},
    "speed_control": {"score": 1.00, "reason": "Tailwind team, 5 fast members"},
    "lead_pair":     {"score": 1.00, "reason": "3 viable lead pairs"},
}

_ANALYSIS = {
    "valid": True,
    "issues": [],
    "roles": {
        "physical_sweeper": 2, "special_sweeper": 1, "tank": 1,
        "hazard_setter": 1, "pivot": 1, "hazard_removal": 0, "support": 0,
    },
    "weaknesses": {},
    "resistances": {},
    "coverage": {"covered_types": ["fire", "water"], "missing_types": ["fairy"]},
}

_MEMBERS = [
    {"pokemon_name": f"poke{i}", "set_id": i, "set_name": None}
    for i in range(1, 7)
]

_OPTIMIZE_RESULT = {
    "best_teams": [
        {
            "score": 9.14,
            "breakdown": _BREAKDOWN,
            "members": _MEMBERS,
            "analysis": _ANALYSIS,
        }
    ],
    "generations_run": 30,
    "initial_population": 50,
    "evaluations": 287,
}


@contextmanager
def _mock_optimize(result=None, raises=None):
    if result is None:
        result = _OPTIMIZE_RESULT
    kw = {"side_effect": raises} if raises is not None else {"return_value": result}
    with (
        patch("src.api.routes.optimization.get_db_connection") as mock_conn,
        patch("src.api.routes.optimization.optimize_team", **kw),
    ):
        mock_conn.return_value.__enter__ = lambda s: MagicMock()
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        yield


class TestOptimizeEndpoint:
    def test_returns_200_for_empty_body(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={})
        assert resp.status_code == 200

    def test_returns_200_with_all_params(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={
                "population_size": 20,
                "generations": 10,
            })
        assert resp.status_code == 200

    def test_response_has_best_teams(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={})
        assert "best_teams" in resp.json()

    def test_response_has_generations_run(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={})
        assert "generations_run" in resp.json()

    def test_response_has_initial_population(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={})
        assert "initial_population" in resp.json()

    def test_evaluations_is_int(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={})
        assert isinstance(resp.json()["evaluations"], int)

    def test_best_teams_has_team_result_shape(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={})
        team = resp.json()["best_teams"][0]
        assert "score" in team
        assert "breakdown" in team
        assert "members" in team
        assert "analysis" in team

    def test_breakdown_has_four_components(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={})
        breakdown = resp.json()["best_teams"][0]["breakdown"]
        assert set(breakdown.keys()) == {"coverage", "defensive", "role", "speed_control", "lead_pair"}

    def test_each_component_has_score_and_reason(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={})
        for key, comp in resp.json()["best_teams"][0]["breakdown"].items():
            assert "score" in comp, f"{key} missing score"
            assert "reason" in comp, f"{key} missing reason"

    def test_oversized_population_clamped_not_rejected(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={"population_size": 500})
        assert resp.status_code == 200

    def test_oversized_generations_clamped_not_rejected(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={"generations": 999})
        assert resp.status_code == 200

    def test_constraint_violation_returns_400(self):
        with _mock_optimize(raises=ValueError("include Pokémon 'unknown' has no competitive set")):
            resp = client.post("/team/optimize", json={
                "constraints": {"include": ["unknown"], "exclude": []}
            })
        assert resp.status_code == 400

    def test_zero_population_size_rejected(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={"population_size": 0})
        assert resp.status_code == 422

    def test_zero_generations_rejected(self):
        with _mock_optimize():
            resp = client.post("/team/optimize", json={"generations": 0})
        assert resp.status_code == 422
