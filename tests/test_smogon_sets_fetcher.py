# tests/test_smogon_sets_fetcher.py
"""Unit tests for smogon_sets_fetcher name translation."""

import pytest
from src.ingestors.smogon_sets_fetcher import _to_smogon_name


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
