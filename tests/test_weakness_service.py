# tests/test_weakness_service.py
"""Unit tests for weakness and resistance analysis."""

import pytest
from unittest.mock import patch
from src.api.models.team import PokemonBuild
from src.api.services.weakness_service import analyze_weaknesses

BASE = {"hp": 250, "attack": 200, "defense": 150,
        "sp_attack": 150, "sp_defense": 150, "speed": 200}


def _build(types):
    return PokemonBuild("x", 1, types, None, None, None, BASE, [])


# Synthetic multiplier maps returned by all_multipliers_against
_ICE_WEAK = {"ice": 2.0, "fire": 0.5, "water": 1.0, "electric": 1.0,
             "grass": 1.0, "ground": 1.0, "rock": 1.0, "flying": 1.0,
             "psychic": 1.0, "bug": 1.0, "ghost": 1.0, "dragon": 1.0,
             "dark": 1.0, "steel": 1.0, "fairy": 1.0, "poison": 1.0,
             "normal": 1.0, "fighting": 1.0}

_FIRE_RESIST = {k: 1.0 for k in _ICE_WEAK}
_FIRE_RESIST["fire"] = 0.5


class TestAnalyzeWeaknesses:

    def test_returns_weaknesses_and_resistances_keys(self):
        with patch("src.api.services.weakness_service.all_multipliers_against",
                   return_value=_ICE_WEAK):
            result = analyze_weaknesses([_build(["ice"])])
        assert "weaknesses" in result
        assert "resistances" in result

    def test_ice_weakness_counted(self):
        """Three Pokémon weak to ice → weaknesses[ice] == 3."""
        with patch("src.api.services.weakness_service.all_multipliers_against",
                   return_value=_ICE_WEAK):
            builds = [_build(["dragon"]), _build(["dragon"]), _build(["dragon"])]
            result = analyze_weaknesses(builds)
        assert result["weaknesses"].get("ice", 0) == 3

    def test_resistance_counted(self):
        with patch("src.api.services.weakness_service.all_multipliers_against",
                   return_value=_FIRE_RESIST):
            result = analyze_weaknesses([_build(["steel"]), _build(["fire"])])
        assert result["resistances"].get("fire", 0) == 2

    def test_neutral_types_not_in_output(self):
        neutral = {k: 1.0 for k in _ICE_WEAK}
        with patch("src.api.services.weakness_service.all_multipliers_against",
                   return_value=neutral):
            result = analyze_weaknesses([_build(["normal"])])
        assert "normal" not in result["weaknesses"]
        assert "normal" not in result["resistances"]

    def test_immunity_counted_as_resistance(self):
        immune = {k: 1.0 for k in _ICE_WEAK}
        immune["electric"] = 0.0
        with patch("src.api.services.weakness_service.all_multipliers_against",
                   return_value=immune):
            result = analyze_weaknesses([_build(["ground"])])
        assert result["resistances"].get("electric", 0) == 1

    def test_empty_team_returns_empty_dicts(self):
        result = analyze_weaknesses([])
        assert result["weaknesses"] == {}
        assert result["resistances"] == {}
