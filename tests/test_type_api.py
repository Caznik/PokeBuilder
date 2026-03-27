# tests/test_type_api.py
"""API integration tests for type effectiveness endpoints.

These tests verify the /types/multiplier and /types/multipliers endpoints
work correctly. They use synthetic data injected into the type_service module
to avoid database dependencies.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.services import type_service


# Minimal synthetic matrix for API testing
SYNTHETIC_TYPE_DATA = {
    "name_to_id": {
        "normal": 1,
        "fire": 2,
        "water": 3,
        "electric": 4,
        "grass": 5,
        "ground": 6,
        "rock": 7,
        "steel": 8,
        "ghost": 9,
        "ice": 10,
    },
    "matrix": {
        # Fire attacks
        (2, 5): 2.0,   # Fire vs Grass = 2.0
        (2, 3): 0.5,   # Fire vs Water = 0.5
        (2, 8): 2.0,   # Fire vs Steel = 2.0
        (2, 2): 0.5,   # Fire vs Fire = 0.5
        (2, 4): 1.0,   # Fire vs Electric = 1.0 (neutral)
        
        # Normal attacks
        (1, 9): 0.0,   # Normal vs Ghost = 0.0
        (1, 7): 0.5,   # Normal vs Rock = 0.5
        (1, 8): 0.5,   # Normal vs Steel = 0.5
        (1, 5): 1.0,   # Normal vs Grass = 1.0 (neutral)
        
        # Electric attacks
        (4, 3): 2.0,   # Electric vs Water = 2.0
        (4, 6): 0.0,   # Electric vs Ground = 0.0
        (4, 5): 0.5,   # Electric vs Grass = 0.5
        (4, 4): 0.5,   # Electric vs Electric = 0.5
        
        # Ground attacks
        (6, 4): 2.0,   # Ground vs Electric = 2.0
        (6, 5): 0.5,   # Ground vs Grass = 0.5
        (6, 7): 0.5,   # Ground vs Rock = 0.5
        
        # Rock attacks
        (7, 2): 0.5,   # Rock vs Fire = 0.5
        (7, 10): 2.0,  # Rock vs Ice = 2.0
        
        # Steel attacks
        (8, 2): 0.5,   # Steel vs Fire = 0.5
        (8, 10): 2.0,  # Steel vs Ice = 2.0
    }
}


@pytest.fixture(scope="module")
def test_client():
    """Create a test client with synthetic data injected."""
    # Save original state
    original_is_loaded = type_service._is_loaded
    original_matrix = type_service._matrix.copy()
    original_name_to_id = type_service._name_to_id.copy()
    original_id_to_name = type_service._id_to_name.copy()
    
    # Inject synthetic data
    type_service._is_loaded = True
    type_service._name_to_id = SYNTHETIC_TYPE_DATA["name_to_id"]
    type_service._id_to_name = {v: k for k, v in SYNTHETIC_TYPE_DATA["name_to_id"].items()}
    type_service._matrix = SYNTHETIC_TYPE_DATA["matrix"]
    
    # Create test client
    client = TestClient(app)
    
    yield client
    
    # Restore original state
    type_service._is_loaded = original_is_loaded
    type_service._matrix = original_matrix
    type_service._name_to_id = original_name_to_id
    type_service._id_to_name = original_id_to_name


class TestMultiplierEndpoint:
    """Tests for GET /types/multiplier endpoint."""
    
    def test_fire_vs_grass(self, test_client):
        """Fire vs Grass = 2.0."""
        response = test_client.get("/types/multiplier?move=fire&defender=grass")
        assert response.status_code == 200
        assert response.json() == {"multiplier": 2.0}
    
    def test_fire_vs_water(self, test_client):
        """Fire vs Water = 0.5."""
        response = test_client.get("/types/multiplier?move=fire&defender=water")
        assert response.status_code == 200
        assert response.json() == {"multiplier": 0.5}
    
    def test_normal_vs_ghost(self, test_client):
        """Normal vs Ghost = 0.0."""
        response = test_client.get("/types/multiplier?move=normal&defender=ghost")
        assert response.status_code == 200
        assert response.json() == {"multiplier": 0.0}
    
    def test_electric_vs_ground(self, test_client):
        """Electric vs Ground = 0.0."""
        response = test_client.get("/types/multiplier?move=electric&defender=ground")
        assert response.status_code == 200
        assert response.json() == {"multiplier": 0.0}
    
    def test_fire_vs_grass_steel_dual_type(self, test_client):
        """Fire vs Grass/Steel = 4.0."""
        response = test_client.get("/types/multiplier?move=fire&defender=grass,steel")
        assert response.status_code == 200
        assert response.json() == {"multiplier": 4.0}
    
    def test_neutral_damage(self, test_client):
        """Fire vs Electric = 1.0 (not in matrix, defaults to neutral)."""
        response = test_client.get("/types/multiplier?move=fire&defender=electric")
        assert response.status_code == 200
        assert response.json() == {"multiplier": 1.0}
    
    def test_case_insensitive(self, test_client):
        """Type names should be case insensitive."""
        response = test_client.get("/types/multiplier?move=FIRE&defender=GRASS")
        assert response.status_code == 200
        assert response.json() == {"multiplier": 2.0}
        
        response = test_client.get("/types/multiplier?move=Fire&defender=Grass")
        assert response.status_code == 200
        assert response.json() == {"multiplier": 2.0}
    
    def test_invalid_type_returns_400(self, test_client):
        """Invalid type names should return 400 error."""
        response = test_client.get("/types/multiplier?move=fire&defender=unknown_type")
        assert response.status_code == 400
        assert "Unknown type" in response.json()["detail"]
    
    def test_missing_move_parameter(self, test_client):
        """Missing 'move' parameter should fail validation."""
        response = test_client.get("/types/multiplier?defender=grass")
        assert response.status_code == 422
    
    def test_missing_defender_parameter(self, test_client):
        """Missing 'defender' parameter should fail validation."""
        response = test_client.get("/types/multiplier?move=fire")
        assert response.status_code == 422


class TestMultipliersEndpoint:
    """Tests for GET /types/multipliers endpoint."""
    
    def test_returns_all_attackers(self, test_client):
        """Should return multipliers for all attacker types."""
        response = test_client.get("/types/multipliers?defender=grass")
        assert response.status_code == 200
        
        data = response.json()
        assert "multipliers" in data
        
        # Should have multipliers for all types in our synthetic set
        multipliers = data["multipliers"]
        assert len(multipliers) == 10
        assert "fire" in multipliers
        assert "water" in multipliers
        assert "normal" in multipliers
    
    def test_ghost_defender_immunity(self, test_client):
        """Ghost should be immune to Normal."""
        response = test_client.get("/types/multipliers?defender=ghost")
        assert response.status_code == 200
        
        data = response.json()
        multipliers = data["multipliers"]
        assert multipliers["normal"] == 0.0
        assert multipliers["fire"] == 1.0  # Neutral to fire
    
    def test_grass_defender_weaknesses(self, test_client):
        """Grass should be weak to Fire, resistant to Electric/Ground."""
        response = test_client.get("/types/multipliers?defender=grass")
        assert response.status_code == 200
        
        data = response.json()
        multipliers = data["multipliers"]
        assert multipliers["fire"] == 2.0       # Weak to fire
        assert multipliers["electric"] == 0.5     # Resists electric
        assert multipliers["ground"] == 0.5       # Resists ground
    
    def test_dual_type_defender(self, test_client):
        """Should calculate product for dual-type defenders."""
        response = test_client.get("/types/multipliers?defender=grass,steel")
        assert response.status_code == 200
        
        data = response.json()
        multipliers = data["multipliers"]
        assert multipliers["fire"] == 4.0  # 2.0 * 2.0
    
    def test_case_insensitive(self, test_client):
        """Type names should be case insensitive."""
        response = test_client.get("/types/multipliers?defender=GRASS")
        assert response.status_code == 200
        
        data = response.json()
        assert data["multipliers"]["fire"] == 2.0
    
    def test_invalid_type_returns_400(self, test_client):
        """Invalid defender type should return 400 error."""
        response = test_client.get("/types/multipliers?defender=unknown_type")
        assert response.status_code == 400
        assert "Unknown type" in response.json()["detail"]
    
    def test_missing_defender_parameter(self, test_client):
        """Missing 'defender' parameter should fail validation."""
        response = test_client.get("/types/multipliers")
        assert response.status_code == 422


class TestEndpointResponseFormat:
    """Tests for response format consistency."""
    
    def test_multiplier_response_format(self, test_client):
        """Multiplier endpoint should return correct JSON structure."""
        response = test_client.get("/types/multiplier?move=fire&defender=grass")
        data = response.json()
        
        assert "multiplier" in data
        assert isinstance(data["multiplier"], (int, float))
    
    def test_multipliers_response_format(self, test_client):
        """Multipliers endpoint should return correct JSON structure."""
        response = test_client.get("/types/multipliers?defender=grass")
        data = response.json()
        
        assert "multipliers" in data
        assert isinstance(data["multipliers"], dict)
        
        for type_name, multiplier in data["multipliers"].items():
            assert isinstance(type_name, str)
            assert isinstance(multiplier, (int, float))
    
    def test_multiplier_values_are_floats(self, test_client):
        """All multiplier values should be floats."""
        response = test_client.get("/types/multipliers?defender=grass")
        data = response.json()
        
        for multiplier in data["multipliers"].values():
            assert isinstance(multiplier, (int, float))


class TestEdgeCases:
    """Edge case tests for API endpoints."""
    
    def test_whitespace_in_defender_types(self, test_client):
        """Should handle whitespace around comma-separated types."""
        response = test_client.get("/types/multiplier?move=fire&defender=grass%2C%20steel")
        assert response.status_code == 200
        assert response.json() == {"multiplier": 4.0}
    
    def test_single_type_in_multipliers_endpoint(self, test_client):
        """Multipliers endpoint should work with single type."""
        response = test_client.get("/types/multipliers?defender=grass")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["multipliers"]) == 10
    
    def test_very_resistant_combo(self, test_client):
        """Can handle multiple resistances."""
        # Fire vs Fire/Water = 0.5 * 0.5 = 0.25
        response = test_client.get("/types/multiplier?move=fire&defender=fire,water")
        assert response.status_code == 200
        assert response.json() == {"multiplier": 0.25}
    
    def test_immune_combo(self, test_client):
        """Any immunity (0.0) in the chain makes total 0.0."""
        # Electric vs Ground/Ground = 0.0 * 0.0 = 0.0
        response = test_client.get("/types/multiplier?move=electric&defender=ground")
        assert response.status_code == 200
        assert response.json() == {"multiplier": 0.0}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
