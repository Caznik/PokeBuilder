# tests/test_battle_log_fetcher.py
"""Unit tests for battle_log_fetcher — HTTP and DB interactions are mocked."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call

import pytest


class TestFetchReplayIds:
    def test_returns_ids_newer_than_since(self):
        from src.ingestors.battle_log_fetcher import fetch_replay_ids

        since = datetime(2026, 5, 1, tzinfo=timezone.utc)
        batch = [
            {"id": "replay-3", "uploadtime": 1777939200},  # 2026-05-05
            {"id": "replay-2", "uploadtime": 1777852800},  # 2026-05-04
            {"id": "replay-1", "uploadtime": 1777680000},  # 2026-05-02
        ]

        with patch("src.ingestors.battle_log_fetcher.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.side_effect = [batch, []]
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            ids = fetch_replay_ids("[Gen 9 Champions] VGC 2026 Reg M-A", since)

        assert ids == ["replay-3", "replay-2", "replay-1"]

    def test_stops_at_since_boundary(self):
        from src.ingestors.battle_log_fetcher import fetch_replay_ids

        since = datetime(2026, 5, 4, tzinfo=timezone.utc)
        batch = [
            {"id": "replay-3", "uploadtime": 1777939200},  # 2026-05-05 — newer
            {"id": "replay-old", "uploadtime": 1777766400},  # 2026-05-03 — older
        ]

        with patch("src.ingestors.battle_log_fetcher.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = batch
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            ids = fetch_replay_ids("[Gen 9 Champions] VGC 2026 Reg M-A", since)

        assert ids == ["replay-3"]

    def test_returns_empty_when_no_new_replays(self):
        from src.ingestors.battle_log_fetcher import fetch_replay_ids

        since = datetime(2026, 5, 10, tzinfo=timezone.utc)
        batch = [{"id": "replay-old", "uploadtime": 1777680000}]  # 2026-05-02 — older

        with patch("src.ingestors.battle_log_fetcher.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = batch
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            ids = fetch_replay_ids("[Gen 9 Champions] VGC 2026 Reg M-A", since)

        assert ids == []


class TestSeedReplay:
    def _make_parsed(self):
        from src.ingestors.showdown_log_parser import (
            ParsedReplay, ParsedTeam, ParsedPokemonDetail
        )
        p1_team = ParsedTeam(
            player="p1",
            team=["koraidon", "flutter-mane", "incineroar", "farigiraf", "urshifu", "rillaboom"],
            brought=["koraidon", "incineroar", "urshifu", "rillaboom"],
            leads=["koraidon", "incineroar"],
            details=[ParsedPokemonDetail(pokemon="koraidon", moves=["collision-course"], item="booster-energy", ability="orichalcum-pulse")],
        )
        p2_team = ParsedTeam(
            player="p2",
            team=["miraidon", "iron-hands", "amoonguss", "tornadus", "landorus-therian", "urshifu"],
            brought=["miraidon", "amoonguss", "tornadus", "iron-hands"],
            leads=["miraidon", "amoonguss"],
            details=[],
        )
        return ParsedReplay(
            replay_id="test-replay-001",
            p1="Player1",
            p2="Player2",
            winner="p1",
            teams=[p1_team, p2_team],
        )

    def test_inserts_battle_replay_row(self):
        from src.ingestors.battle_log_fetcher import seed_replay

        cursor = MagicMock()
        cursor.rowcount = 1
        parsed = self._make_parsed()

        seed_replay(cursor, parsed, regulation_id=1, format_id="[Gen 9 Champions] VGC 2026 Reg M-A", upload_ts=1746403200)

        first_call = cursor.execute.call_args_list[0]
        assert "INSERT INTO battle_replays" in first_call[0][0]

    def test_skips_teams_if_replay_already_exists(self):
        from src.ingestors.battle_log_fetcher import seed_replay

        cursor = MagicMock()
        cursor.rowcount = 0  # ON CONFLICT DO NOTHING → already exists
        parsed = self._make_parsed()

        seed_replay(cursor, parsed, regulation_id=1, format_id="[Gen 9 Champions] VGC 2026 Reg M-A", upload_ts=1746403200)

        # Only one execute call (the replay insert), no team inserts
        assert cursor.execute.call_count == 1
