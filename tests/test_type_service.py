# tests/test_type_service.py
"""Unit tests for type_effectiveness service with synthetic data.

These tests use a minimal, hand-crafted type effectiveness matrix to test
the service layer without requiring a database connection.
"""

import pytest
from src.api.services import type_service


@pytest.fixture
def synthetic_matrix():
    """Create a synthetic type effectiveness matrix for testing.
    
    This matrix contains a subset of the full Pokemon type chart,
    enough to test all functionality without requiring a database.
    """
    # Set up synthetic type mappings
    type_service._name_to_id = {
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
    }
    
    type_service._id_to_name = {v: k for k, v in type_service._name_to_id.items()}
    
    # Set up synthetic effectiveness matrix (attacker_id, defender_id) -> multiplier
    type_service._matrix = {
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
    
    type_service._is_loaded = True
    
    yield
    
    # Cleanup after tests
    type_service._is_loaded = False
    type_service._matrix = {}
    type_service._name_to_id = {}
    type_service._id_to_name = {}


class TestGetMultiplier:
    """Tests for get_multiplier function."""
    
    def test_fire_vs_grass(self, synthetic_matrix):
        """Fire vs Grass should be 2.0 (super effective)."""
        result = type_service.get_multiplier("fire", "grass")
        assert result == 2.0
    
    def test_fire_vs_water(self, synthetic_matrix):
        """Fire vs Water should be 0.5 (not very effective)."""
        result = type_service.get_multiplier("fire", "water")
        assert result == 0.5
    
    def test_normal_vs_ghost(self, synthetic_matrix):
        """Normal vs Ghost should be 0.0 (no effect)."""
        result = type_service.get_multiplier("normal", "ghost")
        assert result == 0.0
    
    def test_electric_vs_ground(self, synthetic_matrix):
        """Electric vs Ground should be 0.0 (no effect)."""
        result = type_service.get_multiplier("electric", "ground")
        assert result == 0.0
    
    def test_neutral_damage(self, synthetic_matrix):
        """Fire vs Electric should be 1.0 (neutral)."""
        result = type_service.get_multiplier("fire", "electric")
        assert result == 1.0
    
    def test_missing_relationship_defaults_to_neutral(self, synthetic_matrix):
        """Missing relationships should default to 1.0."""
        # Water vs Electric is not defined in our synthetic matrix
        result = type_service.get_multiplier("water", "electric")
        assert result == 1.0
    
    def test_get_multiplier_with_ids(self, synthetic_matrix):
        """get_multiplier should accept type IDs as well as names."""
        result = type_service.get_multiplier(2, 5)  # Fire vs Grass by ID
        assert result == 2.0
    
    def test_case_insensitive_names(self, synthetic_matrix):
        """Type names should be case insensitive."""
        result = type_service.get_multiplier("FIRE", "GRASS")
        assert result == 2.0
        
        result = type_service.get_multiplier("Fire", "Grass")
        assert result == 2.0
    
    def test_invalid_type_raises_value_error(self, synthetic_matrix):
        """Invalid type names should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown type"):
            type_service.get_multiplier("fire", "unknown_type")


class TestCalculateDamageMultiplier:
    """Tests for calculate_damage_multiplier function."""
    
    def test_single_type_defender(self, synthetic_matrix):
        """Single type defender - just the direct multiplier."""
        result = type_service.calculate_damage_multiplier("fire", "grass")
        assert result == 2.0
    
    def test_dual_type_super_effective_combo(self, synthetic_matrix):
        """Fire vs Grass/Steel = 2.0 * 2.0 = 4.0."""
        result = type_service.calculate_damage_multiplier("fire", ["grass", "steel"])
        assert result == 4.0
    
    def test_dual_type_resisted_combo(self, synthetic_matrix):
        """Electric vs Grass/Ground = 0.5 * 0.0 = 0.0."""
        result = type_service.calculate_damage_multiplier("electric", ["grass", "ground"])
        assert result == 0.0
    
    def test_normal_vs_rock_steel(self, synthetic_matrix):
        """Normal vs Rock/Steel = 0.5 * 0.5 = 0.25."""
        result = type_service.calculate_damage_multiplier("normal", ["rock", "steel"])
        assert result == 0.25
    
    def test_single_type_as_list(self, synthetic_matrix):
        """Single type in list should work the same as string."""
        result = type_service.calculate_damage_multiplier("fire", ["grass"])
        assert result == 2.0
    
    def test_multiple_type_ids(self, synthetic_matrix):
        """Can use type IDs instead of names."""
        result = type_service.calculate_damage_multiplier(2, [5, 8])  # Fire vs Grass/Steel
        assert result == 4.0


class TestAllMultipliersAgainst:
    """Tests for all_multipliers_against function."""
    
    def test_returns_all_attacker_types(self, synthetic_matrix):
        """Should return multiplier for each attacker type."""
        result = type_service.all_multipliers_against("grass")
        
        # Should have entries for all types in our synthetic set
        assert len(result) == 10
        assert "fire" in result
        assert "water" in result
        assert "normal" in result
    
    def test_grass_defender_weaknesses(self, synthetic_matrix):
        """Grass is weak to Fire, resistant to Electric and Ground."""
        result = type_service.all_multipliers_against("grass")
        
        assert result["fire"] == 2.0      # Weak to fire
        assert result["electric"] == 0.5  # Resists electric
        assert result["ground"] == 0.5    # Resists ground
        assert result["normal"] == 1.0    # Neutral to normal
    
    def test_ghost_defender_immunity(self, synthetic_matrix):
        """Ghost is immune to Normal."""
        result = type_service.all_multipliers_against("ghost")
        
        assert result["normal"] == 0.0  # Immune to normal
        assert result["fire"] == 1.0    # Neutral to fire
    
    def test_dual_type_defender(self, synthetic_matrix):
        """Should calculate product for dual-type defenders."""
        result = type_service.all_multipliers_against(["grass", "steel"])
        
        # Fire vs Grass/Steel = 4.0
        assert result["fire"] == 4.0
    
    def test_returns_sorted_dict(self, synthetic_matrix):
        """Keys should be type names."""
        result = type_service.all_multipliers_against("fire")
        
        # All keys should be strings (type names)
        for key in result:
            assert isinstance(key, str)
            assert key in type_service._name_to_id


class TestGetTypeId:
    """Tests for get_type_id function."""
    
    def test_get_id_by_name(self, synthetic_matrix):
        """Should return correct ID for type name."""
        assert type_service.get_type_id("fire") == 2
        assert type_service.get_type_id("water") == 3
        assert type_service.get_type_id("normal") == 1
    
    def test_get_id_by_id(self, synthetic_matrix):
        """Should return same ID if passed an integer."""
        assert type_service.get_type_id(2) == 2
        assert type_service.get_type_id(5) == 5
    
    def test_case_insensitive(self, synthetic_matrix):
        """Should be case insensitive."""
        assert type_service.get_type_id("FIRE") == 2
        assert type_service.get_type_id("Fire") == 2
    
    def test_invalid_type_raises_error(self, synthetic_matrix):
        """Should raise ValueError for unknown types."""
        with pytest.raises(ValueError, match="Unknown type"):
            type_service.get_type_id("unknown")


class TestGetTypeName:
    """Tests for get_type_name function."""
    
    def test_get_name_by_id(self, synthetic_matrix):
        """Should return correct name for type ID."""
        assert type_service.get_type_name(2) == "fire"
        assert type_service.get_type_name(3) == "water"
        assert type_service.get_type_name(1) == "normal"
    
    def test_invalid_id_raises_error(self, synthetic_matrix):
        """Should raise ValueError for unknown IDs."""
        with pytest.raises(ValueError, match="Unknown type ID"):
            type_service.get_type_name(999)


class TestEdgeCases:
    """Edge case tests."""
    
    def test_empty_defender_types(self, synthetic_matrix):
        """Empty defender types should return 1.0 (neutral)."""
        result = type_service.calculate_damage_multiplier("fire", [])
        assert result == 1.0
    
    def test_triple_type_combo(self, synthetic_matrix):
        """Can handle more than 2 types (though not valid for Pokemon)."""
        # Just testing the multiplication logic
        result = type_service.calculate_damage_multiplier("fire", ["grass", "grass", "grass"])
        assert result == 8.0  # 2.0 * 2.0 * 2.0
    
    def test_very_resistant_combo(self, synthetic_matrix):
        """Multiple resistances can create very low multipliers."""
        # Fire vs Fire/Water = 0.5 * 0.5 = 0.25
        result = type_service.calculate_damage_multiplier("fire", ["fire", "water"])
        assert result == 0.25


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
