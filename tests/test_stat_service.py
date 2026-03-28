# tests/test_stat_service.py
"""Unit tests for stat calculation service with synthetic data.

These tests use a minimal, synthetic setup to test the service layer
without requiring a database connection.
"""

import pytest
from src.api.services import stat_service


@pytest.fixture
def synthetic_base_stats():
    """Create synthetic base stats for testing (Garchomp)."""
    return {
        "hp": 108,
        "attack": 130,
        "defense": 95,
        "sp_attack": 80,
        "sp_defense": 85,
        "speed": 102,
    }


@pytest.fixture
def synthetic_natures():
    """Create synthetic natures for testing."""
    return {
        "hardy": {"increased_stat": None, "decreased_stat": None},
        "jolly": {"increased_stat": "speed", "decreased_stat": "sp_attack"},
        "modest": {"increased_stat": "sp_attack", "decreased_stat": "attack"},
    }


class TestEVValidation:
    """Tests for EV validation."""

    def test_total_ev_over_510_raises_error(self):
        """Total EVs exceeding 510 should raise ValueError."""
        evs = {"attack": 252, "speed": 252, "hp": 10}  # 514 total
        with pytest.raises(ValueError, match="may not exceed 510"):
            stat_service._validate_evs(evs)

    def test_total_ev_exactly_510_is_valid(self):
        """Total EVs of exactly 510 should be valid."""
        evs = {"attack": 252, "speed": 252, "hp": 6}  # 510 total
        stat_service._validate_evs(evs)  # Should not raise

    def test_single_ev_over_252_raises_error(self):
        """Single EV exceeding 252 should raise ValueError."""
        evs = {"attack": 300}
        with pytest.raises(ValueError, match="must be between 0 and 252"):
            stat_service._validate_evs(evs)

    def test_negative_ev_raises_error(self):
        """Negative EV should raise ValueError."""
        evs = {"attack": -1}
        with pytest.raises(ValueError, match="must be between 0 and 252"):
            stat_service._validate_evs(evs)

    def test_valid_evs_pass(self):
        """Valid EVs should pass validation."""
        evs = {"attack": 252, "speed": 252}
        stat_service._validate_evs(evs)  # Should not raise


class TestIVValidation:
    """Tests for IV validation."""

    def test_iv_over_31_raises_error(self):
        """IV exceeding 31 should raise ValueError."""
        ivs = {"attack": 35}
        with pytest.raises(ValueError, match="must be between 0 and 31"):
            stat_service._validate_ivs(ivs)

    def test_negative_iv_raises_error(self):
        """Negative IV should raise ValueError."""
        ivs = {"attack": -1}
        with pytest.raises(ValueError, match="must be between 0 and 31"):
            stat_service._validate_ivs(ivs)

    def test_valid_ivs_pass(self):
        """Valid IVs should pass validation."""
        ivs = {"attack": 31, "defense": 0, "hp": 15}
        stat_service._validate_ivs(ivs)  # Should not raise


class TestNatureModifiers:
    """Tests for nature modifier calculation."""

    def test_neutral_nature_no_change(self):
        """Neutral nature (hardy) should return 1.0 for all stats."""
        nature = {"increased_stat": None, "decreased_stat": None}
        assert stat_service._get_nature_modifier(nature, "attack") == 1.0
        assert stat_service._get_nature_modifier(nature, "speed") == 1.0

    def test_jolly_increases_speed(self):
        """Jolly nature should increase speed by 10%."""
        nature = {"increased_stat": "speed", "decreased_stat": "sp_attack"}
        assert stat_service._get_nature_modifier(nature, "speed") == 1.1

    def test_jolly_decreases_sp_attack(self):
        """Jolly nature should decrease sp_attack by 10%."""
        nature = {"increased_stat": "speed", "decreased_stat": "sp_attack"}
        assert stat_service._get_nature_modifier(nature, "sp_attack") == 0.9

    def test_jolly_neutral_stats(self):
        """Jolly nature should not affect other stats."""
        nature = {"increased_stat": "speed", "decreased_stat": "sp_attack"}
        assert stat_service._get_nature_modifier(nature, "attack") == 1.0
        assert stat_service._get_nature_modifier(nature, "defense") == 1.0


class TestStatFormulas:
    """Tests for stat calculation formulas."""

    def test_hp_formula(self):
        """HP formula should calculate correctly."""
        # Garchomp: base 108, IV 31, EV 0, level 100
        # HP = ((2*108 + 31 + 0/4) * 100/100) + 100 + 10
        # HP = ((216 + 31) * 1) + 110 = 247 + 110 = 357
        result = stat_service._calc_hp(base=108, iv=31, ev=0, level=100)
        assert result == 357

    def test_hp_with_evs(self):
        """HP formula should account for EVs correctly."""
        # Garchomp with 252 HP EVs
        # HP = ((2*108 + 31 + 63) * 100/100) + 100 + 10
        # HP = 310 + 110 = 420
        result = stat_service._calc_hp(base=108, iv=31, ev=252, level=100)
        assert result == 420

    def test_other_stat_formula_neutral_nature(self):
        """Other stat formula should work with neutral nature."""
        # Garchomp Attack: base 130, IV 31, EV 0, level 100
        # Stat = (((2*130 + 31 + 0/4) * 100/100) + 5) * 1.0
        # Stat = (291 + 5) * 1.0 = 296
        result = stat_service._calc_other(base=130, iv=31, ev=0, level=100, nature_mult=1.0)
        assert result == 296

    def test_other_stat_formula_with_evs(self):
        """Other stat formula should account for EVs."""
        # Garchomp Attack: base 130, IV 31, EV 252, level 100
        # Stat = (((2*130 + 31 + 63) * 1) + 5) * 1.0
        # Stat = (354 + 5) * 1.0 = 359
        result = stat_service._calc_other(base=130, iv=31, ev=252, level=100, nature_mult=1.0)
        assert result == 359

    def test_other_stat_with_jolly_nature(self):
        """Other stat formula should apply nature multiplier."""
        # Garchomp Speed: base 102, IV 31, EV 252, level 100, Jolly (1.1x)
        # Stat = (((2*102 + 31 + 63) * 1) + 5) * 1.1
        # Stat = (298 + 5) * 1.1 = 333
        result = stat_service._calc_other(base=102, iv=31, ev=252, level=100, nature_mult=1.1)
        assert result == 333


class TestCalculateStats:
    """Tests for the main calculate_stats function with mocked database."""

    def test_default_garchomp_calculation(self, mocker):
        """Test Garchomp with defaults (IV 31, EV 0, Hardy)."""
        # Mock database connection
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mocker.MagicMock(return_value=False)
        
        # Mock base stats query (Garchomp)
        mock_cursor.fetchone.side_effect = [
            (108, 130, 95, 80, 85, 102),  # base stats
            (None, None),  # nature (hardy - neutral)
        ]
        
        result = stat_service.calculate_stats(
            conn=mock_conn,
            pokemon_name="garchomp",
            level=100,
            nature_name="hardy",
            evs={},
            ivs={},
        )
        
        # Verify results match expected values
        assert result["hp"] == 357
        assert result["attack"] == 296
        assert result["speed"] == 240

    def test_garchomp_competitive_spread(self, mocker):
        """Test Garchomp with competitive spread (252 Atk, 252 Spe, Jolly)."""
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mocker.MagicMock(return_value=False)
        
        mock_cursor.fetchone.side_effect = [
            (108, 130, 95, 80, 85, 102),  # base stats
            ("speed", "sp_attack"),  # nature (jolly)
        ]
        
        result = stat_service.calculate_stats(
            conn=mock_conn,
            pokemon_name="garchomp",
            level=100,
            nature_name="jolly",
            evs={"attack": 252, "speed": 252, "hp": 6},
            ivs={},
        )
        
        # Verify speed is boosted, sp_attack is reduced
        assert result["speed"] > 300  # 333 expected
        assert result["attack"] > 350  # 359 expected
        assert result["sp_attack"] < 180  # 176 expected (0.9x)

    def test_pokemon_not_found(self, mocker):
        """Should raise ValueError if Pokemon not found."""
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mocker.MagicMock(return_value=False)
        
        mock_cursor.fetchone.return_value = None
        
        with pytest.raises(ValueError, match="Pokemon 'unknown' not found"):
            stat_service.calculate_stats(
                conn=mock_conn,
                pokemon_name="unknown",
                level=100,
                nature_name="hardy",
                evs={},
                ivs={},
            )

    def test_nature_not_found(self, mocker):
        """Should raise ValueError if Nature not found."""
        mock_conn = mocker.MagicMock()
        mock_cursor = mocker.MagicMock()
        mock_conn.cursor.return_value.__enter__ = mocker.MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = mocker.MagicMock(return_value=False)
        
        mock_cursor.fetchone.side_effect = [
            (108, 130, 95, 80, 85, 102),  # base stats found
            None,  # nature not found
        ]
        
        with pytest.raises(ValueError, match="Nature 'invalid' not found"):
            stat_service.calculate_stats(
                conn=mock_conn,
                pokemon_name="garchomp",
                level=100,
                nature_name="invalid",
                evs={},
                ivs={},
            )

    def test_ev_overflow_raises_error(self, mocker):
        """Should raise ValueError if EVs exceed 510."""
        mock_conn = mocker.MagicMock()
        
        with pytest.raises(ValueError, match="may not exceed 510"):
            stat_service.calculate_stats(
                conn=mock_conn,
                pokemon_name="garchomp",
                level=100,
                nature_name="hardy",
                evs={"attack": 252, "defense": 252, "speed": 252},  # 756 total
                ivs={},
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
