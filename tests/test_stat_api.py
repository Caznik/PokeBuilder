# tests/test_stat_api.py
"""API integration tests for stat calculation endpoint.

These tests use FastAPI TestClient to test the complete API flow
without requiring a database connection.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from src.api.main import app


# Mock database data
MOCK_GARCHOMP_STATS = (108, 130, 95, 80, 85, 102)  # hp, atk, def, spa, spd, spe

MOCK_NATURES = {
    "hardy": (None, None),
    "jolly": ("speed", "sp_attack"),
    "modest": ("sp_attack", "attack"),
    "adamant": ("attack", "sp_attack"),
}


def create_mock_cursor():
    """Create a mock cursor that returns appropriate data."""
    class MockCursor:
        def __init__(self):
            self.last_query = None
            self.last_params = None
        
        def execute(self, query, params):
            self.last_query = query
            self.last_params = params
        
        def fetchone(self):
            if "FROM pokemon" in self.last_query:
                return MOCK_GARCHOMP_STATS
            elif "FROM natures" in self.last_query:
                nature_name = self.last_params[0].lower() if self.last_params else "hardy"
                return MOCK_NATURES.get(nature_name, (None, None))
            return None
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
    
    return MockCursor()


class MockConnection:
    """Mock database connection."""
    
    def cursor(self):
        return create_mock_cursor()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


@pytest.fixture
def client():
    """Create a TestClient with mocked database."""
    # Patch the database connection before importing/routing
    with patch("src.api.db.get_db_connection", return_value=MockConnection()):
        with TestClient(app) as test_client:
            yield test_client


class TestCalculateEndpoint:
    """Tests for POST /stats/calculate endpoint."""

    def test_default_garchomp_calculation(self, client):
        """Test Garchomp with defaults (IV 31, EV 0, Hardy)."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp",
            "level": 100,
            "nature": "hardy",
            "evs": {},
            "ivs": {}
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "hp" in data
        assert "attack" in data
        assert "defense" in data
        assert "sp_attack" in data
        assert "sp_defense" in data
        assert "speed" in data
        
        # Verify expected values
        assert data["hp"] == 357
        assert data["attack"] == 296
        assert data["speed"] == 240

    def test_garchomp_competitive_spread_jolly(self, client):
        """Test Garchomp with Jolly nature and competitive EV spread."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp",
            "level": 100,
            "nature": "jolly",
            "evs": {
                "attack": 252,
                "speed": 252,
                "hp": 6
            },
            "ivs": {}
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Speed should be boosted by Jolly nature
        assert data["speed"] == 333  # 1.1x boost
        
        # Sp. Attack should be reduced
        assert data["sp_attack"] == 176  # 0.9x reduction
        
        # Attack should be maxed
        assert data["attack"] == 359

    def test_garchomp_modest_nature(self, client):
        """Test Garchomp with Modest nature (boosts sp_attack, reduces attack)."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp",
            "level": 100,
            "nature": "modest",
            "evs": {
                "sp_attack": 252,
                "hp": 252
            },
            "ivs": {}
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Sp. Attack should be boosted
        assert data["sp_attack"] == 284  # 1.1x boost
        
        # Attack should be reduced
        assert data["attack"] == 266  # 0.9x reduction

    def test_level_50_calculation(self, client):
        """Test calculation at level 50."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp",
            "level": 50,
            "nature": "hardy",
            "evs": {},
            "ivs": {}
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # At level 50, stats are roughly half
        assert data["hp"] == 183
        assert data["attack"] == 150

    def test_custom_ivs(self, client):
        """Test calculation with custom IVs (not 31)."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp",
            "level": 100,
            "nature": "hardy",
            "evs": {},
            "ivs": {
                "hp": 0,
                "attack": 0,
                "defense": 0,
                "sp_attack": 0,
                "sp_defense": 0,
                "speed": 0
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # With IV 0, stats should be lower
        assert data["hp"] == 326  # ((2*108 + 0) * 1) + 110
        assert data["attack"] == 265  # ((2*130 + 0) * 1) + 5

    def test_ev_overflow_returns_error(self, client):
        """Total EVs exceeding 510 should return 422 error (Pydantic validation)."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp",
            "evs": {
                "attack": 252,
                "defense": 252,
                "speed": 252  # Total = 756
            }
        })
        
        assert response.status_code == 422
        # Pydantic validation error
        error_detail = response.json()
        assert "detail" in error_detail

    def test_invalid_ev_value_returns_error(self, client):
        """EV over 252 should return 422 error (Pydantic validation)."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp",
            "evs": {
                "attack": 300
            }
        })
        
        assert response.status_code == 422

    def test_invalid_iv_value_returns_error(self, client):
        """IV over 31 should return 422 error (Pydantic validation)."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp",
            "ivs": {
                "attack": 35
            }
        })
        
        assert response.status_code == 422

    def test_invalid_pokemon_returns_error(self, client):
        """Unknown Pokemon should return 400 error."""
        # Create a mock that returns None for pokemon
        class MockCursorNoPokemon:
            def __init__(self):
                self.last_query = None
            
            def execute(self, query, params):
                self.last_query = query
            
            def fetchone(self):
                if "FROM pokemon" in self.last_query:
                    return None
                return (None, None)
            
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                pass

        class MockConnectionNoPokemon:
            def cursor(self):
                return MockCursorNoPokemon()
            
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                pass

        with patch("src.api.db.get_db_connection", return_value=MockConnectionNoPokemon()):
            with TestClient(app) as test_client:
                response = test_client.post("/stats/calculate", json={
                    "pokemon": "unknown_pokemon"
                })
                
                assert response.status_code == 400
                assert "not found" in response.json()["detail"]

    def test_invalid_nature_returns_error(self, client):
        """Unknown Nature should return 400 error."""
        # Create a mock that returns None for nature
        class MockCursorNoNature:
            def __init__(self):
                self.last_query = None
            
            def execute(self, query, params):
                self.last_query = query
            
            def fetchone(self):
                if "FROM pokemon" in self.last_query:
                    return MOCK_GARCHOMP_STATS
                elif "FROM natures" in self.last_query:
                    return None
                return None
            
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                pass

        class MockConnectionNoNature:
            def cursor(self):
                return MockCursorNoNature()
            
            def __enter__(self):
                return self
            
            def __exit__(self, *args):
                pass

        with patch("src.api.db.get_db_connection", return_value=MockConnectionNoNature()):
            with TestClient(app) as test_client:
                response = test_client.post("/stats/calculate", json={
                    "pokemon": "garchomp",
                    "nature": "invalid_nature"
                })
                
                assert response.status_code == 400
                assert "not found" in response.json()["detail"]

    def test_case_insensitive_pokemon_name(self, client):
        """Pokemon names should be case insensitive."""
        for name in ["GARCHOMP", "Garchomp", "garchomp"]:
            response = client.post("/stats/calculate", json={
                "pokemon": name
            })
            assert response.status_code == 200

    def test_case_insensitive_nature_name(self, client):
        """Nature names should be case insensitive."""
        for nature in ["JOLLY", "Jolly", "jolly"]:
            response = client.post("/stats/calculate", json={
                "pokemon": "garchomp",
                "nature": nature
            })
            assert response.status_code == 200


class TestEdgeCases:
    """Edge case tests for the stat calculation endpoint."""

    def test_partial_ev_spread(self, client):
        """Test with only some EVs specified."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp",
            "evs": {
                "attack": 100
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Attack should be higher due to EVs
        assert data["attack"] > 296
        # Other stats should be base (0 EVs)

    def test_partial_iv_spread(self, client):
        """Test with only some IVs specified."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp",
            "ivs": {
                "attack": 0
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Attack should be lower due to IV 0
        assert data["attack"] < 296
        # Other stats should have IV 31

    def test_minimum_level(self, client):
        """Test calculation at minimum level (1)."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp",
            "level": 1,
            "evs": {},
            "ivs": {}
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # At level 1, stats are minimal
        assert data["hp"] >= 11  # Base minimum

    def test_empty_request_uses_defaults(self, client):
        """Empty request should use all defaults."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should match level 100, Hardy, IV 31, EV 0
        assert data["hp"] == 357


class TestResponseFormat:
    """Tests for response format and data types."""

    def test_response_is_valid_json(self, client):
        """Response should be valid JSON."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_all_stats_are_integers(self, client):
        """All stat values should be integers."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp"
        })
        
        data = response.json()
        for stat_name, value in data.items():
            assert isinstance(value, int), f"{stat_name} should be int"

    def test_response_has_all_required_fields(self, client):
        """Response should contain all 6 stat fields."""
        response = client.post("/stats/calculate", json={
            "pokemon": "garchomp"
        })
        
        data = response.json()
        required_fields = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
        
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
