# tests/test_regulation_service.py
"""Unit tests for regulation_service."""

import pytest
from unittest.mock import MagicMock, call, patch

from src.api.services.regulation_service import (
    create_regulation,
    delete_regulation,
    get_allowed_names,
    get_regulation,
    get_regulation_info,
    list_regulations,
    update_regulation,
)


def _make_conn(fetchone_side_effect=None, fetchall_side_effect=None):
    """Build a mock psycopg2 connection with a context-manager cursor."""
    mock_cur = MagicMock()
    if fetchone_side_effect is not None:
        mock_cur.fetchone.side_effect = fetchone_side_effect
    if fetchall_side_effect is not None:
        mock_cur.fetchall.side_effect = fetchall_side_effect
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cur
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cur


# ---------------------------------------------------------------------------
# get_regulation_info
# ---------------------------------------------------------------------------

class TestGetRegulationInfo:
    def test_returns_name_and_allowed_set(self):
        conn, cur = _make_conn(
            fetchone_side_effect=[("Example Regulation",)],
            fetchall_side_effect=[[("bulbasaur",), ("charmander",)]],
        )
        name, allowed = get_regulation_info(conn, 1)
        assert name == "Example Regulation"
        assert allowed == {"bulbasaur", "charmander"}

    def test_allowed_names_are_lowercase(self):
        conn, cur = _make_conn(
            fetchone_side_effect=[("Reg E",)],
            fetchall_side_effect=[[("Bulbasaur",), ("CHARMANDER",)]],
        )
        _, allowed = get_regulation_info(conn, 1)
        assert "bulbasaur" in allowed
        assert "charmander" in allowed

    def test_raises_for_missing_regulation(self):
        conn, cur = _make_conn(fetchone_side_effect=[None])
        with pytest.raises(ValueError, match="does not exist"):
            get_regulation_info(conn, 999)

    def test_empty_allowlist_returns_empty_set(self):
        conn, cur = _make_conn(
            fetchone_side_effect=[("Empty Reg",)],
            fetchall_side_effect=[[]],
        )
        _, allowed = get_regulation_info(conn, 1)
        assert allowed == set()


# ---------------------------------------------------------------------------
# get_allowed_names
# ---------------------------------------------------------------------------

class TestGetAllowedNames:
    def test_delegates_to_get_regulation_info(self):
        conn, cur = _make_conn(
            fetchone_side_effect=[("Reg E",)],
            fetchall_side_effect=[[("pikachu",)]],
        )
        allowed = get_allowed_names(conn, 1)
        assert allowed == {"pikachu"}

    def test_raises_for_missing_regulation(self):
        conn, cur = _make_conn(fetchone_side_effect=[None])
        with pytest.raises(ValueError):
            get_allowed_names(conn, 999)


# ---------------------------------------------------------------------------
# list_regulations
# ---------------------------------------------------------------------------

class TestListRegulations:
    def test_returns_list_of_dicts(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = [(1, "Reg E", "Example"), (2, "Reg F", None)]
        result = list_regulations(cursor)
        assert result == [
            {"id": 1, "name": "Reg E", "description": "Example"},
            {"id": 2, "name": "Reg F", "description": None},
        ]

    def test_returns_empty_list_when_none(self):
        cursor = MagicMock()
        cursor.fetchall.return_value = []
        assert list_regulations(cursor) == []


# ---------------------------------------------------------------------------
# get_regulation
# ---------------------------------------------------------------------------

class TestGetRegulation:
    def test_returns_regulation_with_pokemon(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (1, "Reg E", "Example")
        cursor.fetchall.return_value = [("bulbasaur",), ("charmander",)]
        result = get_regulation(cursor, 1)
        assert result == {
            "id": 1,
            "name": "Reg E",
            "description": "Example",
            "pokemon": ["bulbasaur", "charmander"],
        }

    def test_raises_for_missing_regulation(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        with pytest.raises(ValueError, match="not found"):
            get_regulation(cursor, 999)

    def test_pokemon_list_is_empty_when_no_pokemon(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (1, "Reg E", None)
        cursor.fetchall.return_value = []
        result = get_regulation(cursor, 1)
        assert result["pokemon"] == []


# ---------------------------------------------------------------------------
# create_regulation
# ---------------------------------------------------------------------------

class TestCreateRegulation:
    def _cursor_for_create(self, pokemon_found=None, reg_name="Test Reg", description=None):
        """Build a cursor mock for a successful create_regulation call."""
        cursor = MagicMock()
        # Calls in order:
        # 1. fetchone → duplicate name check (None = no duplicate)
        # 2. fetchall → _resolve_pokemon_ids result
        # 3. fetchone → INSERT RETURNING id
        # 4. fetchone → get_regulation: SELECT regulation row
        # 5. fetchall → get_regulation: SELECT pokemon names
        if pokemon_found is None:
            pokemon_found = [(1, "bulbasaur")]
        cursor.fetchone.side_effect = [None, (1,), (1, reg_name, description)]
        cursor.fetchall.side_effect = [pokemon_found, [("bulbasaur",)]]
        return cursor

    def test_returns_regulation_dict(self):
        cursor = self._cursor_for_create()
        with patch("src.api.services.regulation_service.execute_values"):
            result = create_regulation(cursor, "Test Reg", None, ["bulbasaur"])
        assert result["id"] == 1
        assert result["name"] == "Test Reg"
        assert "bulbasaur" in result["pokemon"]

    def test_raises_on_unknown_pokemon_name(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [None]  # no duplicate
        cursor.fetchall.side_effect = [[]]    # no pokemon found → all unknown
        with pytest.raises(ValueError, match="unknown Pokémon names"):
            create_regulation(cursor, "Test Reg", None, ["fakemon"])

    def test_error_lists_all_unknown_names(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [None]
        cursor.fetchall.side_effect = [[]]
        with pytest.raises(ValueError) as exc_info:
            create_regulation(cursor, "Test Reg", None, ["fakemon", "notreal"])
        assert "fakemon" in str(exc_info.value)
        assert "notreal" in str(exc_info.value)

    def test_raises_on_duplicate_name(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)  # duplicate found
        with pytest.raises(ValueError, match="already exists"):
            create_regulation(cursor, "Test Reg", None, ["bulbasaur"])


# ---------------------------------------------------------------------------
# update_regulation
# ---------------------------------------------------------------------------

class TestUpdateRegulation:
    def test_raises_for_missing_regulation(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        with pytest.raises(ValueError, match="not found"):
            update_regulation(cursor, 999, None, None, None)

    def test_raises_on_unknown_pokemon_in_names(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(1,), None]  # exists, then no pokemon found
        cursor.fetchall.side_effect = [[]]           # _resolve_pokemon_ids: none found
        with pytest.raises(ValueError, match="unknown Pokémon names"):
            update_regulation(cursor, 1, None, None, ["fakemon"])

    def test_returns_updated_regulation(self):
        cursor = MagicMock()
        # exists check, _resolve_pokemon_ids result, get_regulation row, get_regulation pokemon
        cursor.fetchone.side_effect = [(1,), (1, "New Name", None)]
        cursor.fetchall.side_effect = [[(1, "bulbasaur")], [("bulbasaur",)]]
        with patch("src.api.services.regulation_service.execute_values"):
            result = update_regulation(cursor, 1, "New Name", None, ["bulbasaur"])
        assert result["name"] == "New Name"

    def test_pokemon_names_none_leaves_list_unchanged(self):
        cursor = MagicMock()
        cursor.fetchone.side_effect = [(1,), (1, "Reg E", None)]
        cursor.fetchall.side_effect = [[("bulbasaur",)]]
        result = update_regulation(cursor, 1, None, None, None)
        assert result["pokemon"] == ["bulbasaur"]


# ---------------------------------------------------------------------------
# delete_regulation
# ---------------------------------------------------------------------------

class TestDeleteRegulation:
    def test_raises_for_missing_regulation(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        with pytest.raises(ValueError, match="not found"):
            delete_regulation(cursor, 999)

    def test_executes_delete_for_existing_regulation(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (1,)
        delete_regulation(cursor, 1)
        delete_call = [c for c in cursor.execute.call_args_list
                       if "DELETE" in str(c)]
        assert len(delete_call) == 1
