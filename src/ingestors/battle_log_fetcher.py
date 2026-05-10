# src/ingestors/battle_log_fetcher.py
"""Ingest VGC battle replays from Pokémon Showdown into the database.

Usage:
    python -m src.ingestors.battle_log_fetcher
    python -m src.ingestors.battle_log_fetcher --format "[Gen 9 Champions] VGC 2026 Reg M-A"
"""

import argparse
import json
import logging
import os
from datetime import datetime, timezone

import psycopg2
import requests

from .showdown_log_parser import ParsedReplay, parse_log

logger = logging.getLogger(__name__)

SEARCH_URL = "https://replay.pokemonshowdown.com/api/replays/search"
REPLAY_URL_TEMPLATE = "https://replay.pokemonshowdown.com/{replay_id}.json"
INGESTOR_NAME = "battle_log_fetcher"
REQUEST_TIMEOUT = 15
DEFAULT_FORMAT = "[Gen 9 Champions] VGC 2026 Reg M-A"

FORMAT_TO_REGULATION: dict[str, str] = {
    "[Gen 9 Champions] VGC 2026 Reg M-A": "Regulation M-A",
}

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def _get_checkpoint(cursor) -> datetime:
    """Return last_run_at for this ingestor, creating the row if absent.

    Args:
        cursor: Active psycopg2 cursor.

    Returns:
        datetime of the last successful run.
    """
    cursor.execute(
        "INSERT INTO ingestion_checkpoints (ingestor) VALUES (%s) ON CONFLICT (ingestor) DO NOTHING",
        (INGESTOR_NAME,),
    )
    cursor.execute(
        "SELECT last_run_at FROM ingestion_checkpoints WHERE ingestor = %s",
        (INGESTOR_NAME,),
    )
    return cursor.fetchone()[0]


def _update_checkpoint(cursor, count: int) -> None:
    """Advance last_run_at to NOW and accumulate the ingested count.

    Args:
        cursor: Active psycopg2 cursor.
        count: Number of replays ingested in this run.
    """
    cursor.execute(
        """
        UPDATE ingestion_checkpoints
        SET last_run_at = NOW(), replays_ingested = replays_ingested + %s
        WHERE ingestor = %s
        """,
        (count, INGESTOR_NAME),
    )


def _resolve_regulation_id(cursor, format_id: str) -> int | None:
    """Look up the DB regulation id for a Showdown format string.

    Args:
        cursor: Active psycopg2 cursor.
        format_id: Showdown format string.

    Returns:
        Integer regulation id, or None if the format is unrecognised.
    """
    regulation_name = FORMAT_TO_REGULATION.get(format_id)
    if not regulation_name:
        return None
    cursor.execute(
        "SELECT id FROM regulations WHERE name = %s", (regulation_name,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def fetch_replay_ids(format_id: str, since: datetime) -> list[str]:
    """Paginate Showdown replay search and return IDs uploaded after since.

    Args:
        format_id: Showdown format string.
        since: Only include replays uploaded strictly after this timestamp.

    Returns:
        List of replay IDs in reverse chronological order.
    """
    ids: list[str] = []
    page = 1
    while True:
        resp = requests.get(
            SEARCH_URL,
            params={"format": format_id, "page": page},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        if not resp.text.strip():
            break
        try:
            text = resp.text.lstrip("]")
            batch = json.loads(text)
        except Exception:
            logger.warning(
                "Non-JSON response from search API (status=%s, body=%r)",
                resp.status_code,
                resp.text[:300],
            )
            break
        if not batch:
            break
        for item in batch:
            upload_dt = datetime.fromtimestamp(item["uploadtime"], tz=timezone.utc)
            if upload_dt <= since:
                return ids
            ids.append(item["id"])
        page += 1
    return ids


def fetch_replay_json(replay_id: str) -> dict:
    """Fetch full replay JSON from Showdown.

    Args:
        replay_id: Showdown replay ID string.

    Returns:
        Parsed JSON dict with keys id, p1, p2, log, uploadtime, format.

    Raises:
        requests.HTTPError: On non-2xx responses.
    """
    url = REPLAY_URL_TEMPLATE.format(replay_id=replay_id)
    resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def seed_replay(
    cursor,
    parsed: ParsedReplay,
    regulation_id: int | None,
    format_id: str,
    upload_ts: int,
) -> None:
    """Insert one parsed replay and its teams/details idempotently.

    Skips all child inserts if the replay ID already exists (ON CONFLICT
    DO NOTHING on the battle_replays PK sets rowcount to 0).

    Args:
        cursor: Active psycopg2 cursor.
        parsed: ParsedReplay from showdown_log_parser.
        regulation_id: DB regulation id (None if unknown format).
        format_id: Showdown format string.
        upload_ts: Unix timestamp from the Showdown JSON.
    """
    cursor.execute(
        """
        INSERT INTO battle_replays (id, regulation_id, p1, p2, winner, uploaded_at, format)
        VALUES (%s, %s, %s, %s, %s, to_timestamp(%s), %s)
        ON CONFLICT (id) DO NOTHING
        """,
        (
            parsed.replay_id, regulation_id, parsed.p1, parsed.p2,
            parsed.winner, upload_ts, format_id,
        ),
    )
    if cursor.rowcount == 0:
        return

    for team in parsed.teams:
        cursor.execute(
            """
            INSERT INTO battle_teams (replay_id, player, team, brought, leads)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (parsed.replay_id, team.player, team.team, team.brought, team.leads),
        )
        for d in team.details:
            cursor.execute(
                """
                INSERT INTO battle_pokemon_details
                    (replay_id, player, pokemon, moves, item, ability)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (parsed.replay_id, team.player, d.pokemon, d.moves, d.item, d.ability),
            )


def ingest(format_id: str, conn) -> int:
    """Fetch and store all new replays for a format since the last checkpoint.

    Args:
        format_id: Showdown format string.
        conn: Active psycopg2 connection.

    Returns:
        Number of replays successfully ingested.
    """
    with conn.cursor() as cursor:
        since = _get_checkpoint(cursor)
        regulation_id = _resolve_regulation_id(cursor, format_id)
        conn.commit()

    replay_ids = fetch_replay_ids(format_id, since)
    total = len(replay_ids)
    logger.info("Found %d new replays since %s", total, since)

    ingested = 0
    failed = 0
    for i, replay_id in enumerate(replay_ids, start=1):
        try:
            data = fetch_replay_json(replay_id)
            p1, p2 = data["players"][0], data["players"][1]
            parsed = parse_log(replay_id, p1, p2, data["log"])
            with conn.cursor() as cursor:
                seed_replay(cursor, parsed, regulation_id, format_id, data["uploadtime"])
            conn.commit()
            ingested += 1
            if ingested % 50 == 0 or i == total:
                logger.info("[%d/%d] ingested=%d failed=%d", i, total, ingested, failed)
        except Exception as exc:
            failed += 1
            logger.warning("[%d/%d] Failed %s: %s", i, total, replay_id, exc)
            conn.rollback()

    if ingested > 0:
        with conn.cursor() as cursor:
            _update_checkpoint(cursor, ingested)
        conn.commit()
    logger.info("Done — ingested=%d failed=%d total=%d", ingested, failed, total)
    return ingested


def main() -> None:
    """Fetch VGC replays from Pokémon Showdown and seed them into the database."""
    parser = argparse.ArgumentParser(description="Ingest Showdown battle replays")
    parser.add_argument("--format", default=DEFAULT_FORMAT, help="Showdown format string")
    args = parser.parse_args()

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )
    try:
        count = ingest(args.format, conn)
        logger.info("Ingested %d replays.", count)
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
