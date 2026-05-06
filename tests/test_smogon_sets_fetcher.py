# tests/test_smogon_sets_fetcher.py
"""Unit tests for smogon_sets_fetcher name translation and moveset extraction."""

import pytest
from src.ingestors.smogon_sets_fetcher import _to_smogon_name, _extract_movesets


class TestToSmogonName:

    @pytest.mark.parametrize("db_name,expected", [
        # --- suffix stripping: default forms ---
        ("deoxys-normal",              "deoxys"),
        ("wormadam-plant",             "wormadam"),
        ("shaymin-land",               "shaymin"),
        ("basculin-red-striped",       "basculin"),
        ("darmanitan-standard",        "darmanitan"),
        ("darmanitan-galar-standard",  "darmanitan-galar"),
        ("tornadus-incarnate",         "tornadus"),
        ("thundurus-incarnate",        "thundurus"),
        ("landorus-incarnate",         "landorus"),
        ("enamorus-incarnate",         "enamorus"),
        ("keldeo-ordinary",            "keldeo"),
        ("meloetta-aria",              "meloetta"),
        ("aegislash-shield",           "aegislash"),
        ("pumpkaboo-average",          "pumpkaboo"),
        ("gourgeist-average",          "gourgeist"),
        ("zygarde-50",                 "zygarde"),
        ("oricorio-baile",             "oricorio"),
        ("lycanroc-midday",            "lycanroc"),
        ("wishiwashi-solo",            "wishiwashi"),
        ("mimikyu-disguised",          "mimikyu"),
        ("eiscue-ice",                 "eiscue"),
        ("morpeko-full-belly",         "morpeko"),
        ("urshifu-single-strike",      "urshifu"),
        ("palafin-zero",               "palafin"),
        ("tatsugiri-curly",            "tatsugiri"),
        ("dudunsparce-two-segment",    "dudunsparce"),
        ("maushold-family-of-four",    "maushold"),
        ("maushold-family-of-three",   "maushold"),
        ("squawkabilly-green-plumage", "squawkabilly"),
        ("squawkabilly-blue-plumage",  "squawkabilly"),
        ("squawkabilly-yellow-plumage","squawkabilly"),
        ("squawkabilly-white-plumage", "squawkabilly"),
        # --- suffix stripping: -breed (tauros paldea forms) ---
        ("tauros-paldea-combat-breed", "tauros-paldea-combat"),
        ("tauros-paldea-blaze-breed",  "tauros-paldea-blaze"),
        ("tauros-paldea-aqua-breed",   "tauros-paldea-aqua"),
        # --- suffix stripping: -mask (ogerpon forms) ---
        ("ogerpon-wellspring-mask",    "ogerpon-wellspring"),
        ("ogerpon-hearthflame-mask",   "ogerpon-hearthflame"),
        ("ogerpon-cornerstone-mask",   "ogerpon-cornerstone"),
        # --- suffix stripping: -female variants ---
        ("meowstic-female",            "meowstic"),
        ("indeedee-female",            "indeedee"),
        ("basculegion-female",         "basculegion"),
        ("oinkologne-female",          "oinkologne"),
        # --- explicit overrides ---
        ("giratina-altered",           "giratina-origin"),
        ("frillish-male",              "frillish"),
        ("jellicent-male",             "jellicent"),
        ("indeedee-male",              "indeedee"),
        ("basculegion-male",           "basculegion"),
        ("oinkologne-male",            "oinkologne"),
        # --- no change: base names or gender-differentiated slugs ---
        ("garchomp",                   "garchomp"),
        ("pyroar-male",                "pyroar-male"),
        ("meowstic-male",              "meowstic-male"),
        ("toxtricity-amped",           "toxtricity-amped"),
        ("giratina-origin",            "giratina-origin"),
    ])
    def test_name_translation(self, db_name, expected):
        assert _to_smogon_name(db_name) == expected


def _make_dex_settings(strategies: list[dict]) -> dict:
    """Build a minimal dexSettings structure for testing."""
    return {"injectRpcs": [None, None, [None, {"strategies": strategies}]]}


def _moveset(name: str = "Offensive") -> dict:
    return {
        "name": name,
        "abilities": ["Rough Skin"],
        "items": ["Choice Scarf"],
        "natures": ["Jolly"],
        "moveslots": [[{"move": "Earthquake", "type": "Ground"}]],
        "evconfigs": [{"hp": 0, "atk": 252, "def": 0, "spa": 0, "spd": 4, "spe": 252}],
    }


class TestExtractMovesets:

    def test_each_moveset_carries_its_strategy_format(self):
        """format from the strategy should be attached to every moveset it contains."""
        dex = _make_dex_settings([
            {"format": "VGC 2025 Reg G", "movesets": [_moveset("Scarf"), _moveset("Life Orb")]},
        ])
        result = _extract_movesets(dex)
        assert len(result) == 2
        assert result[0]["format"] == "VGC 2025 Reg G"
        assert result[1]["format"] == "VGC 2025 Reg G"

    def test_different_strategies_carry_different_formats(self):
        """Movesets from different strategies must carry their respective format tags."""
        dex = _make_dex_settings([
            {"format": "OU", "movesets": [_moveset("Scarf")]},
            {"format": "VGC 2025 Reg G", "movesets": [_moveset("VGC Scarf")]},
        ])
        result = _extract_movesets(dex)
        assert len(result) == 2
        formats = {ms["name"]: ms["format"] for ms in result}
        assert formats["Scarf"] == "OU"
        assert formats["VGC Scarf"] == "VGC 2025 Reg G"

    def test_missing_format_field_defaults_to_none(self):
        """Strategies without a format key should produce None on each moveset."""
        dex = _make_dex_settings([
            {"movesets": [_moveset()]},
        ])
        result = _extract_movesets(dex)
        assert len(result) == 1
        assert result[0]["format"] is None

    def test_empty_strategies_returns_empty_list(self):
        dex = _make_dex_settings([])
        assert _extract_movesets(dex) == []

    def test_strategy_with_no_movesets_key_skipped(self):
        dex = _make_dex_settings([
            {"format": "OU"},
            {"format": "VGC 2025 Reg G", "movesets": [_moveset()]},
        ])
        result = _extract_movesets(dex)
        assert len(result) == 1
        assert result[0]["format"] == "VGC 2025 Reg G"
