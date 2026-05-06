# tests/test_vgc_sets_fetcher.py
"""Unit tests for vgc_sets_fetcher — normalization, parsing, and DB persistence."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.ingestors.vgc_sets_fetcher import (
    _normalize,
    _parse_ev_spread,
    _to_pikalytics_slug,
    _get_regulation_pokemon,
    _parse_pokemon_page,
    _fetch_pokemon_page,
    _store_vgc_set,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


INDIVIDUAL_PAGE_FIXTURE = """
<html><body>
<div class="container-column">
  <div>
    <p class="pika-static">Top Moves</p>
    <div>Earthquake<span>75.3%</span></div>
    <div>Dragon Claw<span>62.1%</span></div>
    <div>Protect<span>58.9%</span></div>
    <div>Rock Slide<span>47.2%</span></div>
  </div>
  <div>
    <p class="pika-static">Top Abilities</p>
    <div>Rough Skin<span>92.4%</span></div>
    <div>Sand Veil<span>7.6%</span></div>
  </div>
  <div>
    <p class="pika-static">Top Items</p>
    <div>Choice Scarf<span>38.1%</span></div>
    <div>Life Orb<span>29.4%</span></div>
  </div>
  <div>
    <p class="pika-static">Top Natures</p>
    <div>Jolly<span>71.2%</span></div>
    <div>Adamant<span>28.8%</span></div>
  </div>
  <div>
    <p class="pika-static">Top EV Spreads</p>
    <div>252 Atk / 252 Spe / 4 HP<span>44.3%</span></div>
    <div>4 HP / 252 Atk / 252 Spe<span>22.1%</span></div>
  </div>
</div>
</body></html>
"""

EMPTY_PAGE_FIXTURE = "<html><body></body></html>"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_conn(cursor):
    """Build a mock connection whose cursor() context manager yields cursor."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=cursor)
    ctx.__exit__ = MagicMock(return_value=False)
    conn = MagicMock()
    conn.cursor.return_value = ctx
    return conn


def _make_mock_response(text: str, raise_exc=None):
    """Build a mock requests.Response."""
    resp = MagicMock()
    if raise_exc:
        resp.raise_for_status.side_effect = raise_exc
    else:
        resp.raise_for_status.return_value = None
        resp.text = text
    return resp


# ---------------------------------------------------------------------------
# TestNormalize
# ---------------------------------------------------------------------------

class TestNormalize:

    def test_lowercase_conversion(self):
        assert _normalize("Garchomp") == "garchomp"

    def test_spaces_become_hyphens(self):
        assert _normalize("Flutter Mane") == "flutter-mane"

    def test_apostrophe_removal(self):
        assert _normalize("Farfetch'd") == "farfetchd"

    def test_dot_removal(self):
        assert _normalize("Mr. Mime") == "mr-mime"

    def test_multiple_spaces_collapsed(self):
        assert _normalize("Iron  Hands") == "iron-hands"

    def test_multiple_hyphens_collapsed(self):
        assert _normalize("Porygon--Z") == "porygon-z"

    def test_leading_trailing_hyphens_stripped(self):
        assert _normalize("-garchomp-") == "garchomp"

    def test_already_normalized(self):
        assert _normalize("iron-hands") == "iron-hands"


# ---------------------------------------------------------------------------
# TestToPikalyticsSlug
# ---------------------------------------------------------------------------

class TestToPikalyticsSlug:

    @pytest.mark.parametrize("db_name,expected", [
        # -breed suffix (Tauros Paldea forms)
        ("tauros-paldea-combat-breed", "tauros-paldea-combat"),
        ("tauros-paldea-blaze-breed",  "tauros-paldea-blaze"),
        ("tauros-paldea-aqua-breed",   "tauros-paldea-aqua"),
        # other common PokeAPI default-form suffixes
        ("tornadus-incarnate",         "tornadus"),
        ("darmanitan-standard",        "darmanitan"),
        ("aegislash-shield",           "aegislash"),
        ("urshifu-single-strike",      "urshifu"),
        ("morpeko-full-belly",         "morpeko"),
        ("maushold-family-of-four",    "maushold"),
        ("ogerpon-wellspring-mask",    "ogerpon-wellspring"),
        # base names pass through unchanged
        ("garchomp",                   "garchomp"),
        ("incineroar",                 "incineroar"),
        ("tauros",                     "tauros"),
        # regional forms are preserved (they are distinct species)
        ("darmanitan-galar-standard",  "darmanitan-galar"),
    ])
    def test_slug_translation(self, db_name, expected):
        assert _to_pikalytics_slug(db_name) == expected


# ---------------------------------------------------------------------------
# TestParseEvSpread
# ---------------------------------------------------------------------------

class TestParseEvSpread:

    def test_atk_spe_hp(self):
        result = _parse_ev_spread("252 Atk / 252 Spe / 4 HP")
        assert result == {
            "attack": 252, "speed": 252, "hp": 4,
            "defense": 0, "sp_attack": 0, "sp_defense": 0,
        }

    def test_spa_spd_spe(self):
        result = _parse_ev_spread("252 SpA / 4 SpD / 252 Spe")
        assert result == {
            "sp_attack": 252, "sp_defense": 4, "speed": 252,
            "hp": 0, "attack": 0, "defense": 0,
        }

    def test_empty_string_all_zeros(self):
        result = _parse_ev_spread("")
        assert result == {
            "hp": 0, "attack": 0, "defense": 0,
            "sp_attack": 0, "sp_defense": 0, "speed": 0,
        }

    def test_single_stat(self):
        result = _parse_ev_spread("252 HP")
        assert result["hp"] == 252
        assert result["attack"] == 0
        assert result["speed"] == 0

    def test_all_six_stats_always_present(self):
        result = _parse_ev_spread("4 Def")
        assert set(result.keys()) == {"hp", "attack", "defense", "sp_attack", "sp_defense", "speed"}


# ---------------------------------------------------------------------------
# TestGetRegulationPokemon
# ---------------------------------------------------------------------------

class TestGetRegulationPokemon:

    def _make_conn(self, rows: list[tuple]) -> MagicMock:
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=cursor)
        ctx.__exit__ = MagicMock(return_value=False)
        conn = MagicMock()
        conn.cursor.return_value = ctx
        return conn

    def test_returns_pokemon_names_for_known_regulation(self):
        conn = self._make_conn([("garchomp",), ("incineroar",), ("pelipper",)])
        result = _get_regulation_pokemon(conn, "Regulation M-A")
        assert result == ["garchomp", "incineroar", "pelipper"]

    def test_returns_empty_list_when_regulation_not_found(self):
        conn = self._make_conn([])
        result = _get_regulation_pokemon(conn, "Unknown Regulation")
        assert result == []

    def test_query_uses_case_insensitive_match(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [("pikachu",)]
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=cursor)
        ctx.__exit__ = MagicMock(return_value=False)
        conn = MagicMock()
        conn.cursor.return_value = ctx

        _get_regulation_pokemon(conn, "regulation m-a")

        sql = cursor.execute.call_args[0][0]
        assert "LOWER" in sql


# ---------------------------------------------------------------------------
# TestParsePokemonPage
# ---------------------------------------------------------------------------

class TestParsePokemonPage:

    def test_moves(self):
        result = _parse_pokemon_page(INDIVIDUAL_PAGE_FIXTURE)
        assert result["moves"] == ["Earthquake", "Dragon Claw", "Protect", "Rock Slide"]

    def test_ability(self):
        result = _parse_pokemon_page(INDIVIDUAL_PAGE_FIXTURE)
        assert result["ability"] == "Rough Skin"

    def test_item(self):
        result = _parse_pokemon_page(INDIVIDUAL_PAGE_FIXTURE)
        assert result["item"] == "Choice Scarf"

    def test_nature(self):
        result = _parse_pokemon_page(INDIVIDUAL_PAGE_FIXTURE)
        assert result["nature"] == "Jolly"

    def test_ev_spread(self):
        result = _parse_pokemon_page(INDIVIDUAL_PAGE_FIXTURE)
        assert result["ev_spread"] == "252 Atk / 252 Spe / 4 HP"

    def test_empty_page_returns_defaults(self):
        result = _parse_pokemon_page(EMPTY_PAGE_FIXTURE)
        assert result["moves"] == []
        assert result["ability"] == ""
        assert result["item"] == ""
        assert result["nature"] == ""
        assert result["ev_spread"] == ""

    def test_result_has_all_expected_keys(self):
        result = _parse_pokemon_page(INDIVIDUAL_PAGE_FIXTURE)
        assert set(result.keys()) == {"moves", "ability", "item", "nature", "ev_spread"}


# ---------------------------------------------------------------------------
# TestFetchPokemonPage
# ---------------------------------------------------------------------------

class TestFetchPokemonPage:

    def test_returns_parsed_dict_on_success(self):
        mock_resp = _make_mock_response(INDIVIDUAL_PAGE_FIXTURE)
        with patch("src.ingestors.vgc_sets_fetcher.session.get", return_value=mock_resp):
            result = _fetch_pokemon_page("garchomp", "sv-vgc-2025-reg-g")
        assert result is not None
        assert result["ability"] == "Rough Skin"
        assert result["nature"] == "Jolly"
        assert len(result["moves"]) == 4

    def test_returns_none_on_http_error(self):
        mock_resp = _make_mock_response("", raise_exc=requests.HTTPError("404"))
        with patch("src.ingestors.vgc_sets_fetcher.session.get", return_value=mock_resp):
            result = _fetch_pokemon_page("missingno", "sv-vgc-2025-reg-g")
        assert result is None

    def test_returns_none_on_connection_error(self):
        with patch(
            "src.ingestors.vgc_sets_fetcher.session.get",
            side_effect=requests.ConnectionError("timeout"),
        ):
            result = _fetch_pokemon_page("garchomp", "sv-vgc-2025-reg-g")
        assert result is None

    def test_strips_breed_suffix_from_url(self):
        """tauros-paldea-combat-breed should fetch from tauros-paldea-combat URL."""
        mock_resp = _make_mock_response(INDIVIDUAL_PAGE_FIXTURE)
        with patch("src.ingestors.vgc_sets_fetcher.session.get", return_value=mock_resp) as mock_get:
            _fetch_pokemon_page("tauros-paldea-combat-breed", "gen9championsvgc2026regma")
        called_url = mock_get.call_args[0][0]
        assert "tauros-paldea-combat-breed" not in called_url
        assert "tauros-paldea-combat" in called_url

    def test_falls_back_to_mega_slug_on_404(self):
        """When the base slug 404s, the -mega variant should be tried."""
        not_found = _make_mock_response("", raise_exc=requests.HTTPError("404"))
        mega_ok = _make_mock_response(INDIVIDUAL_PAGE_FIXTURE)
        with patch(
            "src.ingestors.vgc_sets_fetcher.session.get",
            side_effect=[not_found, mega_ok],
        ):
            result = _fetch_pokemon_page("beedrill", "sv-vgc-2025-reg-g")
        assert result is not None
        assert result["ability"] == "Rough Skin"

    def test_returns_none_when_both_base_and_mega_fail(self):
        """If both base and -mega slugs 404, return None."""
        not_found = _make_mock_response("", raise_exc=requests.HTTPError("404"))
        with patch(
            "src.ingestors.vgc_sets_fetcher.session.get",
            side_effect=[not_found, not_found],
        ):
            result = _fetch_pokemon_page("emboar", "sv-vgc-2025-reg-g")
        assert result is None


# ---------------------------------------------------------------------------
# TestStoreVgcSet
# ---------------------------------------------------------------------------

_SAMPLE_PAGE_DATA = {
    "moves": ["Earthquake", "Dragon Claw", "Protect", "Rock Slide"],
    "ability": "Rough Skin",
    "item": "Choice Scarf",
    "nature": "Jolly",
    "ev_spread": "252 Atk / 252 Spe / 4 HP",
}


class TestStoreVgcSet:

    def test_happy_path_returns_true_and_commits(self):
        cursor = MagicMock()
        # pokemon(1), nature(2), ability(3), INSERT RETURNING set_id(10),
        # move1(11), move2(12), move3(13), move4(14)
        cursor.fetchone.side_effect = [
            (1,), (2,), (3,), (10,),
            (11,), (12,), (13,), (14,),
        ]
        conn = _make_mock_conn(cursor)

        result = _store_vgc_set(conn, "garchomp", _SAMPLE_PAGE_DATA, "VGC 2025 Reg G")

        assert result is True
        conn.commit.assert_called_once()

    def test_pokemon_not_found_returns_false_no_commit(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        conn = _make_mock_conn(cursor)

        result = _store_vgc_set(conn, "unknown-mon", _SAMPLE_PAGE_DATA, "VGC 2025 Reg G")

        assert result is False
        conn.commit.assert_not_called()

    def test_missing_move_warns_and_still_stores(self, caplog):
        cursor = MagicMock()
        # pokemon(1), nature(2), ability(3), INSERT RETURNING(10),
        # move1(11), move2=None (not found), move3(12), move4(13)
        cursor.fetchone.side_effect = [
            (1,), (2,), (3,), (10,),
            (11,), None, (12,), (13,),
        ]
        conn = _make_mock_conn(cursor)

        with caplog.at_level(logging.WARNING):
            result = _store_vgc_set(conn, "garchomp", _SAMPLE_PAGE_DATA, "VGC 2025 Reg G")

        assert result is True
        conn.commit.assert_called_once()
        assert "not in DB" in caplog.text

    def test_delete_scoped_to_regulation_name(self):
        """DELETE must target only the specific regulation, not all VGC sets."""
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            (1,), (2,), (3,), (10,),
            (11,), (12,), (13,), (14,),
        ]
        conn = _make_mock_conn(cursor)
        _store_vgc_set(conn, "garchomp", _SAMPLE_PAGE_DATA, "Regulation M-A")

        calls = cursor.execute.call_args_list
        delete_call = next(c for c in calls if "DELETE" in str(c))
        sql = delete_call[0][0]
        params = delete_call[0][1]
        assert "LOWER(format)" in sql
        assert "regulation m-a" in str(params).lower()

    def test_delete_called_before_insert(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            (1,), (2,), (3,), (10,),
            (11,), (12,), (13,), (14,),
        ]
        conn = _make_mock_conn(cursor)
        _store_vgc_set(conn, "garchomp", _SAMPLE_PAGE_DATA, "VGC 2025 Reg G")

        calls = [str(c) for c in cursor.execute.call_args_list]
        delete_idx = next(i for i, c in enumerate(calls) if "DELETE" in c)
        insert_idx = next(i for i, c in enumerate(calls) if "INSERT INTO competitive_sets" in c)
        assert delete_idx < insert_idx
