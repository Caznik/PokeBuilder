# tests/test_generation_api.py
"""API integration tests for POST /team/generate."""

from unittest.mock import MagicMock, patch
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_result(n_teams=1, weakness_count=1):
    teams = []
    for i in range(n_teams):
        teams.append({
            "score": round(7.5 - weakness_count * 0.5, 2),
            "breakdown": {
                "coverage":      {"score": 0.11, "reason": "missing fairy"},
                "defensive":     {"score": round(1.0 - weakness_count * 0.2, 2),
                                  "reason": f"{weakness_count} Pokémon weak to fire"},
                "role":          {"score": 1.00, "reason": "all role minimums met"},
                "speed_control": {"score": 0.50, "reason": "limited speed control (1 fast, 0 priority)"},
                "lead_pair":     {"score": 1.00, "reason": "2 viable lead pairs"},
            },
            "members": [
                {"pokemon_name": "garchomp",   "set_id": 1, "set_name": "Choice Scarf"},
                {"pokemon_name": "ferrothorn", "set_id": 2, "set_name": "Defensive"},
                {"pokemon_name": "rotom-wash", "set_id": 3, "set_name": "Defensive"},
                {"pokemon_name": "clefable",   "set_id": 4, "set_name": "Calm Mind"},
                {"pokemon_name": "heatran",    "set_id": 5, "set_name": "Stealth Rock"},
                {"pokemon_name": "landorus",   "set_id": 6, "set_name": "Scarf"},
            ],
            "analysis": {
                "valid": True,
                "issues": [],
                "roles": {
                    "physical_sweeper": 2, "special_sweeper": 1, "tank": 1,
                    "hazard_setter": 1, "pivot": 1, "hazard_removal": 0, "support": 0,
                },
                "weaknesses": {"fire": weakness_count},
                "resistances": {"steel": 3},
                "coverage": {
                    "covered_types": ["grass", "steel"],
                    "missing_types": ["fairy"],
                },
            },
        })
    return {"teams": teams, "generated": 10, "valid_found": n_teams}


@contextmanager
def _mock_generate(result):
    with (
        patch("src.api.routes.generation.get_db_connection") as mock_conn,
        patch("src.api.routes.generation.generate_teams", return_value=result) as mock_gen,
    ):
        mock_conn.return_value.__enter__ = lambda s: MagicMock()
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)
        yield mock_gen


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGenerateEndpoint:
    def test_no_body_returns_200(self):
        with _mock_generate(_valid_result()):
            resp = client.post("/team/generate")
        assert resp.status_code == 200

    def test_empty_body_returns_200(self):
        with _mock_generate(_valid_result()):
            resp = client.post("/team/generate", json={})
        assert resp.status_code == 200

    def test_body_with_constraints_returns_200(self):
        with _mock_generate(_valid_result()):
            resp = client.post(
                "/team/generate",
                json={"constraints": {"include": ["garchomp"], "exclude": ["mewtwo"]}},
            )
        assert resp.status_code == 200

    def test_response_has_teams_list(self):
        with _mock_generate(_valid_result()):
            resp = client.post("/team/generate")
        assert "teams" in resp.json()
        assert isinstance(resp.json()["teams"], list)

    def test_response_has_metadata_fields(self):
        with _mock_generate(_valid_result()):
            resp = client.post("/team/generate")
        body = resp.json()
        assert "generated" in body
        assert "valid_found" in body

    def test_team_has_score_members_analysis(self):
        with _mock_generate(_valid_result()):
            resp = client.post("/team/generate")
        team = resp.json()["teams"][0]
        assert "score" in team
        assert "members" in team
        assert "analysis" in team

    def test_member_has_required_fields(self):
        with _mock_generate(_valid_result()):
            resp = client.post("/team/generate")
        member = resp.json()["teams"][0]["members"][0]
        assert "pokemon_name" in member
        assert "set_id" in member
        assert "set_name" in member

    def test_analysis_has_required_fields(self):
        with _mock_generate(_valid_result()):
            resp = client.post("/team/generate")
        analysis = resp.json()["teams"][0]["analysis"]
        assert "valid" in analysis
        assert "issues" in analysis
        assert "roles" in analysis
        assert "weaknesses" in analysis
        assert "resistances" in analysis
        assert "coverage" in analysis

    def test_coverage_has_covered_and_missing(self):
        with _mock_generate(_valid_result()):
            resp = client.post("/team/generate")
        coverage = resp.json()["teams"][0]["analysis"]["coverage"]
        assert "covered_types" in coverage
        assert "missing_types" in coverage

    def test_invalid_include_returns_400(self):
        with (
            patch("src.api.routes.generation.get_db_connection") as mock_conn,
            patch(
                "src.api.routes.generation.generate_teams",
                side_effect=ValueError("include Pokémon 'unknown' has no competitive set"),
            ),
        ):
            mock_conn.return_value.__enter__ = lambda s: MagicMock()
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            resp = client.post(
                "/team/generate",
                json={"constraints": {"include": ["unknown"]}},
            )
        assert resp.status_code == 400
        assert "include" in resp.json()["detail"]

    def test_pool_too_small_returns_400(self):
        with (
            patch("src.api.routes.generation.get_db_connection") as mock_conn,
            patch(
                "src.api.routes.generation.generate_teams",
                side_effect=ValueError("Pool has only 2 distinct Pokémon"),
            ),
        ):
            mock_conn.return_value.__enter__ = lambda s: MagicMock()
            mock_conn.return_value.__exit__ = MagicMock(return_value=False)
            resp = client.post("/team/generate")
        assert resp.status_code == 400

    def test_empty_teams_list_is_valid_200(self):
        result = {"teams": [], "generated": 100, "valid_found": 0}
        with _mock_generate(result):
            resp = client.post("/team/generate")
        assert resp.status_code == 200
        assert resp.json()["teams"] == []
        assert resp.json()["valid_found"] == 0

    def test_score_is_float(self):
        with _mock_generate(_valid_result()):
            resp = client.post("/team/generate")
        assert isinstance(resp.json()["teams"][0]["score"], float)

    def test_team_has_breakdown_with_four_components(self):
        with _mock_generate(_valid_result()):
            resp = client.post("/team/generate")
        breakdown = resp.json()["teams"][0]["breakdown"]
        assert set(breakdown.keys()) == {"coverage", "defensive", "role", "speed_control", "lead_pair"}

    def test_breakdown_components_have_score_and_reason(self):
        with _mock_generate(_valid_result()):
            resp = client.post("/team/generate")
        for comp in resp.json()["teams"][0]["breakdown"].values():
            assert "score" in comp
            assert "reason" in comp

    def test_multiple_teams_returned(self):
        with _mock_generate(_valid_result(n_teams=3)):
            resp = client.post("/team/generate")
        assert len(resp.json()["teams"]) == 3
