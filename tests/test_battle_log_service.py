"""Unit tests for battle_log_service — all DB calls mocked."""

from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from src.api.models.battle_log import BattleLogCreate, BattleLogOut
from src.api.services.battle_log_service import (
    create_log,
    delete_log,
    get_log,
    list_logs,
)

_NOW = datetime(2026, 5, 12, 10, 0, 0, tzinfo=timezone.utc)

_BODY_SINGLES = BattleLogCreate(
    format="singles",
    brought_pokemon=["charizard", "blastoise", "venusaur"],
    enemy_team=["pikachu", "mewtwo"],
    result="win",
)

_BODY_VGC = BattleLogCreate(
    format="vgc",
    brought_pokemon=["charizard", "blastoise", "venusaur", "snorlax"],
    enemy_team=["pikachu", "mewtwo", "mew"],
    result="loss",
)

_DB_ROW = (
    1,          # id
    42,         # user_id
    None,       # saved_team_id
    None,       # saved_team_name
    None,       # regulation_id
    "singles",  # format
    ["charizard", "blastoise", "venusaur"],  # brought_pokemon
    ["pikachu", "mewtwo"],                   # enemy_team
    [],         # enemy_brought
    "win",      # result
    None,       # notes
    _NOW,       # played_at
    [],         # saved_team_members
)


def _make_conn(fetchone_val=None, fetchall_val=None, rowcount=1):
    """Build a MagicMock connection whose cursor behaves as a context manager."""
    cur = MagicMock()
    cur.fetchone.return_value = fetchone_val
    cur.fetchall.return_value = fetchall_val if fetchall_val is not None else []
    cur.rowcount = rowcount
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)

    conn = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


class TestCreateLog:
    def test_returns_battle_log_out(self):
        """create_log returns a BattleLogOut with the inserted row's data."""
        conn, cur = _make_conn(fetchone_val=(1,))
        # Second fetchone is the SELECT after INSERT
        cur.fetchone.side_effect = [(1,), _DB_ROW]

        result = create_log(conn, user_id=42, body=_BODY_SINGLES)

        assert isinstance(result, BattleLogOut)
        assert result.id == 1
        assert result.format == "singles"
        assert result.result == "win"

    def test_commits_after_insert(self):
        """create_log calls conn.commit() after the INSERT."""
        conn, cur = _make_conn(fetchone_val=(1,))
        cur.fetchone.side_effect = [(1,), _DB_ROW]

        create_log(conn, user_id=42, body=_BODY_SINGLES)

        conn.commit.assert_called_once()

    def test_insert_uses_parameterized_query(self):
        """create_log passes user data as parameters, not string interpolation."""
        conn, cur = _make_conn()
        cur.fetchone.side_effect = [(1,), _DB_ROW]

        create_log(conn, user_id=42, body=_BODY_SINGLES)

        first_call_args = cur.execute.call_args_list[0]
        sql, params = first_call_args[0]
        assert "%s" in sql
        assert 42 in params


class TestListLogs:
    def test_no_filters_returns_all(self):
        """list_logs with no filters returns all user's logs."""
        conn, cur = _make_conn(fetchall_val=[_DB_ROW])

        result = list_logs(conn, user_id=42)

        assert len(result) == 1
        assert isinstance(result[0], BattleLogOut)

    def test_empty_result_returns_empty_list(self):
        """list_logs returns [] when no logs exist."""
        conn, cur = _make_conn(fetchall_val=[])

        result = list_logs(conn, user_id=42)

        assert result == []

    def test_format_filter_adds_where_clause(self):
        """list_logs with format='singles' includes format in query params."""
        conn, cur = _make_conn(fetchall_val=[_DB_ROW])

        list_logs(conn, user_id=42, format="singles")

        call_args = cur.execute.call_args
        sql, params = call_args[0]
        assert "format" in sql.lower()
        assert "singles" in params

    def test_result_filter_adds_where_clause(self):
        """list_logs with result='win' includes result in query params."""
        conn, cur = _make_conn(fetchall_val=[_DB_ROW])

        list_logs(conn, user_id=42, result="win")

        call_args = cur.execute.call_args
        sql, params = call_args[0]
        assert "result" in sql.lower()
        assert "win" in params

    def test_regulation_id_filter_adds_where_clause(self):
        """list_logs with regulation_id=5 includes regulation in query params."""
        conn, cur = _make_conn(fetchall_val=[_DB_ROW])

        list_logs(conn, user_id=42, regulation_id=5)

        call_args = cur.execute.call_args
        sql, params = call_args[0]
        assert "regulation_id" in sql.lower()
        assert 5 in params


class TestGetLog:
    def test_found_returns_battle_log_out(self):
        """get_log returns BattleLogOut when the log exists and belongs to user."""
        conn, cur = _make_conn(fetchone_val=_DB_ROW)

        result = get_log(conn, log_id=1, user_id=42)

        assert isinstance(result, BattleLogOut)
        assert result.id == 1

    def test_not_found_raises_value_error(self):
        """get_log raises ValueError when log does not exist or belongs to another user."""
        conn, cur = _make_conn(fetchone_val=None)

        with pytest.raises(ValueError, match="1"):
            get_log(conn, log_id=1, user_id=42)


class TestDeleteLog:
    def test_success_does_not_raise(self):
        """delete_log completes without raising when the log exists."""
        conn, cur = _make_conn(rowcount=1)

        delete_log(conn, log_id=1, user_id=42)  # should not raise

        conn.commit.assert_called_once()

    def test_not_found_raises_value_error(self):
        """delete_log raises ValueError when the log does not exist or is not owned by user."""
        conn, cur = _make_conn(rowcount=0)

        with pytest.raises(ValueError, match="1"):
            delete_log(conn, log_id=1, user_id=42)
