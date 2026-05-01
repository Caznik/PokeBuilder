# tests/test_saved_team_api.py
"""API integration tests for /saved-teams endpoints."""

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models.saved_team import SavedTeamDetail, SavedTeamSummary, SavedTeamMember
from src.api.models.team import TeamAnalysisResponse, CoverageResult
from src.api.models.scoring import ScoreBreakdown, ScoreComponent

client = TestClient(app)

_NOW = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)
_SCORE_COMPONENT = ScoreComponent(score=1.0, reason="test")
_BREAKDOWN = ScoreBreakdown(
    coverage=_SCORE_COMPONENT, defensive=_SCORE_COMPONENT,
    role=_SCORE_COMPONENT, speed_control=_SCORE_COMPONENT, lead_pair=_SCORE_COMPONENT,
)
_ANALYSIS = TeamAnalysisResponse(
    valid=True, issues=[], roles={"physical_sweeper": 2},
    weaknesses={"ice": 1}, resistances={"steel": 2},
    coverage=CoverageResult(covered_types=["fire"], missing_types=["fairy"]),
    speed_control_archetype="tailwind",
)
_MEMBERS = [SavedTeamMember(slot=i, pokemon_name=f"pokemon{i}", set_id=i + 1) for i in range(6)]
_DETAIL = SavedTeamDetail(
    id=1, name="My Team", score=8.5, created_at=_NOW,
    members=_MEMBERS, breakdown=_BREAKDOWN, analysis=_ANALYSIS,
)
_SUMMARY = SavedTeamSummary(id=1, name="My Team", score=8.5, created_at=_NOW, members=_MEMBERS)

_VALID_SAVE_PAYLOAD = {
    "name": "My Team",
    "members": [{"pokemon_name": f"pokemon{i}", "set_id": i + 1} for i in range(6)],
    "score": 8.5,
    "breakdown": {
        "coverage":      {"score": 1.0, "reason": "test"},
        "defensive":     {"score": 1.0, "reason": "test"},
        "role":          {"score": 1.0, "reason": "test"},
        "speed_control": {"score": 1.0, "reason": "test"},
        "lead_pair":     {"score": 1.0, "reason": "test"},
    },
    "analysis": {
        "valid": True, "issues": [], "roles": {"physical_sweeper": 2},
        "weaknesses": {"ice": 1}, "resistances": {"steel": 2},
        "coverage": {"covered_types": ["fire"], "missing_types": ["fairy"]},
        "speed_control_archetype": "tailwind",
    },
}


@contextmanager
def _mock_db():
    yield MagicMock()


class TestSaveEndpoint:
    def test_post_returns_201(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.save_team", return_value=_DETAIL),
        ):
            resp = client.post("/saved-teams/", json=_VALID_SAVE_PAYLOAD)
        assert resp.status_code == 201

    def test_post_wrong_member_count_returns_422(self):
        bad_payload = {**_VALID_SAVE_PAYLOAD, "members": [{"pokemon_name": "a", "set_id": 1}]}
        resp = client.post("/saved-teams/", json=bad_payload)
        assert resp.status_code == 422

    def test_post_empty_name_returns_422(self):
        bad_payload = {**_VALID_SAVE_PAYLOAD, "name": "   "}
        resp = client.post("/saved-teams/", json=bad_payload)
        assert resp.status_code == 422


class TestListEndpoint:
    def test_get_returns_200_and_list(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.list_teams", return_value=[_SUMMARY]),
        ):
            resp = client.get("/saved-teams/")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert data[0]["name"] == "My Team"

    def test_get_returns_empty_list(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.list_teams", return_value=[]),
        ):
            resp = client.get("/saved-teams/")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetEndpoint:
    def test_get_by_id_returns_200(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.get_team", return_value=_DETAIL),
        ):
            resp = client.get("/saved-teams/1")
        assert resp.status_code == 200
        assert resp.json()["id"] == 1

    def test_get_missing_returns_404(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.get_team", side_effect=ValueError("not found")),
        ):
            resp = client.get("/saved-teams/999")
        assert resp.status_code == 404


class TestUpdateEndpoint:
    def test_patch_name_returns_200(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.update_team", return_value=_DETAIL),
        ):
            resp = client.patch("/saved-teams/1", json={"name": "New Name"})
        assert resp.status_code == 200

    def test_patch_empty_body_returns_422(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.update_team", return_value=_DETAIL),
        ):
            resp = client.patch("/saved-teams/1", json={})
        assert resp.status_code == 422

    def test_patch_missing_returns_404(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.update_team", side_effect=ValueError("not found")),
        ):
            resp = client.patch("/saved-teams/1", json={"name": "X"})
        assert resp.status_code == 404


class TestUpdateMemberEndpoint:
    def test_patch_slot_returns_200(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.update_member", return_value=_DETAIL),
        ):
            resp = client.patch(
                "/saved-teams/1/members/0",
                json={"pokemon_name": "rillaboom", "set_id": 7},
            )
        assert resp.status_code == 200

    def test_patch_invalid_slot_returns_422(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.update_member", return_value=_DETAIL),
        ):
            resp = client.patch(
                "/saved-teams/1/members/6",
                json={"pokemon_name": "rillaboom", "set_id": 7},
            )
        assert resp.status_code == 422

    def test_patch_slot_missing_team_returns_404(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.update_member", side_effect=ValueError("not found")),
        ):
            resp = client.patch(
                "/saved-teams/999/members/0",
                json={"pokemon_name": "rillaboom", "set_id": 7},
            )
        assert resp.status_code == 404


class TestDeleteEndpoint:
    def test_delete_returns_204(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.delete_team", return_value=None),
        ):
            resp = client.delete("/saved-teams/1")
        assert resp.status_code == 204

    def test_delete_missing_returns_404(self):
        with (
            patch("src.api.routes.saved_teams.get_db_connection", return_value=_mock_db()),
            patch("src.api.routes.saved_teams.delete_team", side_effect=ValueError("not found")),
        ):
            resp = client.delete("/saved-teams/999")
        assert resp.status_code == 404
