# tests/test_regulation_m_a_fetcher.py
"""Unit tests for regulation_m_a_fetcher — normalization, parsing, seeding."""

import logging
from unittest.mock import MagicMock, patch

import pytest

FIXTURE_HTML = """
<html><body>
<table class="dextable">
<tr>
  <td><a href="/pokedex-champions/bulbasaur/"><img src="/art/001.png" /></a></td>
  <td><a href="/pokedex-champions/charizard/"><img src="/art/006.png" /></a></td>
  <td><a href="/pokedex-champions/ditto/"><img src="/art/132.png" /></a></td>
  <td><a href="/pokedex-champions/nidoran-f/"><img src="/art/029.png" /></a></td>
  <td><a href="/pokedex-champions/nidoran-m/"><img src="/art/032.png" /></a></td>
  <td><a href="/pokedex-champions/farfetchd/"><img src="/art/083.png" /></a></td>
  <td><a href="/pokedex-champions/mr-mime/"><img src="/art/122.png" /></a></td>
  <td><a href="/pokedex-champions/porygon-z/"><img src="/art/474.png" /></a></td>
  <td><a href="/pokedex-champions/flabebe/"><img src="/art/669.png" /></a></td>
  <td><a href="/pokedex-champions/mime-jr/"><img src="/art/439.png" /></a></td>
  <td><a href="/pokedex-champions/grass.shtml">Grass</a></td>
  <td><a href="/pokedex-champions/">Index</a></td>
</tr>
</table>
</body></html>
"""


class TestNormalizeName:
    def test_basic_lowercase(self):
        from src.ingestors.regulation_m_a_fetcher import normalize_name
        assert normalize_name("Charizard") == "charizard"

    def test_nidoran_female(self):
        from src.ingestors.regulation_m_a_fetcher import normalize_name
        assert normalize_name("Nidoran♀") == "nidoran-f"

    def test_nidoran_male(self):
        from src.ingestors.regulation_m_a_fetcher import normalize_name
        assert normalize_name("Nidoran♂") == "nidoran-m"

    def test_farfetchd(self):
        from src.ingestors.regulation_m_a_fetcher import normalize_name
        assert normalize_name("Farfetch'd") == "farfetchd"

    def test_mr_mime(self):
        from src.ingestors.regulation_m_a_fetcher import normalize_name
        assert normalize_name("Mr. Mime") == "mr-mime"

    def test_porygon_z_preserved(self):
        from src.ingestors.regulation_m_a_fetcher import normalize_name
        assert normalize_name("Porygon-Z") == "porygon-z"

    def test_accented_chars_stripped(self):
        from src.ingestors.regulation_m_a_fetcher import normalize_name
        assert normalize_name("Flabébé") == "flabebe"

    def test_mime_jr(self):
        from src.ingestors.regulation_m_a_fetcher import normalize_name
        assert normalize_name("Mime Jr.") == "mime-jr"

    def test_type_null(self):
        from src.ingestors.regulation_m_a_fetcher import normalize_name
        assert normalize_name("Type: Null") == "type-null"


class TestParsePokemonNames:
    def test_extracts_known_names(self):
        from src.ingestors.regulation_m_a_fetcher import parse_pokemon_names
        names = parse_pokemon_names(FIXTURE_HTML)
        assert "charizard" in names
        assert "bulbasaur" in names
        assert "ditto" in names

    def test_extracts_hyphenated_slugs(self):
        from src.ingestors.regulation_m_a_fetcher import parse_pokemon_names
        names = parse_pokemon_names(FIXTURE_HTML)
        assert "nidoran-f" in names
        assert "nidoran-m" in names
        assert "farfetchd" in names
        assert "mr-mime" in names
        assert "porygon-z" in names
        assert "flabebe" in names
        assert "mime-jr" in names

    def test_ignores_non_pokemon_links(self):
        from src.ingestors.regulation_m_a_fetcher import parse_pokemon_names
        names = parse_pokemon_names(FIXTURE_HTML)
        assert "grass" not in names
        assert "" not in names

    def test_no_duplicates(self):
        from src.ingestors.regulation_m_a_fetcher import parse_pokemon_names
        names = parse_pokemon_names(FIXTURE_HTML)
        assert len(names) == len(set(names))
        assert len(names) == 10

    def test_empty_html_returns_empty(self):
        from src.ingestors.regulation_m_a_fetcher import parse_pokemon_names
        assert parse_pokemon_names("<html><body></body></html>") == []


class TestFetchPokemonNames:
    def test_raises_on_http_error(self):
        from src.ingestors.regulation_m_a_fetcher import fetch_pokemon_names
        import requests
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        with patch("requests.get", return_value=mock_response):
            with pytest.raises(requests.HTTPError):
                fetch_pokemon_names("http://fake-url")

    def test_returns_parsed_names(self):
        from src.ingestors.regulation_m_a_fetcher import fetch_pokemon_names
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.text = FIXTURE_HTML
        with patch("requests.get", return_value=mock_response):
            names = fetch_pokemon_names("http://fake-url")
        assert "charizard" in names


class TestGetPokemonIds:
    def test_returns_matched_ids(self):
        from src.ingestors.regulation_m_a_fetcher import _get_pokemon_ids
        cursor = MagicMock()
        cursor.fetchall.return_value = [(6, "charizard"), (132, "ditto")]
        result = _get_pokemon_ids(cursor, ["charizard", "ditto"])
        assert result == {"charizard": 6, "ditto": 132}

    def test_warns_on_unknown_names(self, caplog):
        from src.ingestors.regulation_m_a_fetcher import _get_pokemon_ids
        cursor = MagicMock()
        cursor.fetchall.return_value = [(6, "charizard")]
        with caplog.at_level(logging.WARNING):
            result = _get_pokemon_ids(cursor, ["charizard", "unknown-mon"])
        assert "unknown-mon" in caplog.text
        assert "unknown-mon" not in result

    def test_empty_names_returns_empty(self):
        from src.ingestors.regulation_m_a_fetcher import _get_pokemon_ids
        cursor = MagicMock()
        result = _get_pokemon_ids(cursor, [])
        cursor.execute.assert_not_called()
        assert result == {}


class TestSeed:
    def test_inserts_regulation_and_associations(self):
        from src.ingestors.regulation_m_a_fetcher import seed
        cursor = MagicMock()
        cursor.fetchone.return_value = (42,)

        with patch("src.ingestors.regulation_m_a_fetcher._get_pokemon_ids", return_value={"charizard": 6}) as mock_ids, \
             patch("src.ingestors.regulation_m_a_fetcher.execute_values") as mock_ev:
            seed(cursor, ["charizard"])

        mock_ids.assert_called_once_with(cursor, ["charizard"])
        rows = mock_ev.call_args[0][2]
        assert (42, 6) in rows

    def test_skips_execute_values_when_no_pokemon(self):
        from src.ingestors.regulation_m_a_fetcher import seed
        cursor = MagicMock()
        cursor.fetchone.return_value = (42,)

        with patch("src.ingestors.regulation_m_a_fetcher._get_pokemon_ids", return_value={}), \
             patch("src.ingestors.regulation_m_a_fetcher.execute_values") as mock_ev:
            seed(cursor, [])

        mock_ev.assert_not_called()

    def test_falls_back_to_select_when_conflict(self):
        from src.ingestors.regulation_m_a_fetcher import seed
        cursor = MagicMock()
        # First fetchone (RETURNING id) returns None → regulation already exists
        # Second fetchone (SELECT id) returns the existing id
        cursor.fetchone.side_effect = [None, (99,)]

        with patch("src.ingestors.regulation_m_a_fetcher._get_pokemon_ids", return_value={"ditto": 132}), \
             patch("src.ingestors.regulation_m_a_fetcher.execute_values") as mock_ev:
            seed(cursor, ["ditto"])

        rows = mock_ev.call_args[0][2]
        assert (99, 132) in rows
