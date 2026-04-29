# tests/test_score_api.py
"""API integration tests for POST /team/score."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)

_TEAM_6 = [
    {"pokemon_name": "garchomp",   "set_id": 1},
    {"pokemon_name": "ferrothorn", "set_id": 2},
    {"pokemon_name": "rotom-wash", "set_id": 3},
    {"pokemon_name": "clefable",   "set_id": 4},
    {"pokemon_name": "heatran",    "set_id": 5},
    {"pokemon_name": "landorus",   "set_id": 6},
]

_ANALYSIS = {
    "valid": True,
    "issues": [],
    "roles": {
        "physical_sweeper": 2, "special_sweeper": 1, "tank": 1,
        "hazard_setter": 1, "pivot": 1, "hazard_removal": 0, "support": 0,
    },
    "weaknesses": {"fire": 1},
    "resistances": {"steel": 3},
    "coverage": {
        "covered_types": ["grass", "steel", "fire"],
        "missing_types": ["fairy"],
    },
}

_SCORE_RESULT = {
    "score": 7.5,
    "breakdown": {
        "coverage":      {"score": 0.17, "reason": "missing fairy"},
        "defensive":     {"score": 0.80, "reason": "1 Pokémon weak to fire"},
        "role":          {"score": 1.00, "reason": "all role minimums met"},
        "speed_control": {"score": 1.00, "reason": "2 fast Pokémon, 0 priority user(s)"},
        "lead_pair":     {"score": 1.00, "reason": "3 viable lead pairs"},
    },
}


@contextmanager
def _mock_score(score_result=None, analysis=None, load_raises=None):
    if score_result is None:
        score_result = _SCORE_RESULT
    if analysis is None:
        analysis = _ANALYSIS

    load_kw = (
        {"side_effect": load_raises}
        if load_raises is not None
        else {"return_value": [MagicMock()] * 6}
    )

    with (
        patch("src.api.routes.scoring.get_db_connection") as mock_conn,
        patch("src.api.routes.scoring.load_team", **load_kw),
        patch("src.api.routes.scoring.analyze_team", return_value=analysis),
        patch("src.api.routes.scoring.score_team", return_value=score_result),
    ):
        mock_conn.return_value.__enter__ = lambda s: MagicMock()
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        yield


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestScoreEndpoint:
    def test_valid_team_returns_200(self):
        with _mock_score():
            resp = client.post("/team/score", json=_TEAM_6)
        assert resp.status_code == 200

    def test_response_has_score(self):
        with _mock_score():
            resp = client.post("/team/score", json=_TEAM_6)
        assert "score" in resp.json()

    def test_response_has_breakdown(self):
        with _mock_score():
            resp = client.post("/team/score", json=_TEAM_6)
        assert "breakdown" in resp.json()

    def test_response_has_analysis(self):
        with _mock_score():
            resp = client.post("/team/score", json=_TEAM_6)
        assert "analysis" in resp.json()

    def test_breakdown_has_four_components(self):
        with _mock_score():
            resp = client.post("/team/score", json=_TEAM_6)
        breakdown = resp.json()["breakdown"]
        assert set(breakdown.keys()) == {"coverage", "defensive", "role", "speed_control", "lead_pair"}

    def test_each_component_has_score_and_reason(self):
        with _mock_score():
            resp = client.post("/team/score", json=_TEAM_6)
        for key, comp in resp.json()["breakdown"].items():
            assert "score" in comp, f"{key} missing score"
            assert "reason" in comp, f"{key} missing reason"

    def test_score_is_float(self):
        with _mock_score():
            resp = client.post("/team/score", json=_TEAM_6)
        assert isinstance(resp.json()["score"], float)

    def test_five_members_returns_422(self):
        resp = client.post("/team/score", json=_TEAM_6[:5])
        assert resp.status_code == 422

    def test_seven_members_returns_422(self):
        extra = _TEAM_6 + [{"pokemon_name": "extra", "set_id": 7}]
        resp = client.post("/team/score", json=extra)
        assert resp.status_code == 422

    def test_invalid_set_id_returns_404(self):
        with _mock_score(load_raises=ValueError("set 999 not found")):
            resp = client.post("/team/score", json=_TEAM_6)
        assert resp.status_code == 404

    def test_analysis_has_required_fields(self):
        with _mock_score():
            resp = client.post("/team/score", json=_TEAM_6)
        analysis = resp.json()["analysis"]
        for field in ("valid", "issues", "roles", "weaknesses", "resistances", "coverage"):
            assert field in analysis

    def test_analysis_coverage_has_covered_and_missing(self):
        with _mock_score():
            resp = client.post("/team/score", json=_TEAM_6)
        coverage = resp.json()["analysis"]["coverage"]
        assert "covered_types" in coverage
        assert "missing_types" in coverage

    def test_component_score_is_float(self):
        with _mock_score():
            resp = client.post("/team/score", json=_TEAM_6)
        for comp in resp.json()["breakdown"].values():
            assert isinstance(comp["score"], float)

    def test_component_reason_is_string(self):
        with _mock_score():
            resp = client.post("/team/score", json=_TEAM_6)
        for comp in resp.json()["breakdown"].values():
            assert isinstance(comp["reason"], str)
