# src/ingestors/regulations_seeder.py
"""Idempotent seeder for VGC regulations.

Defines named regulations as lists of Pokémon names. Each run is safe to
re-run — existing rows are skipped via ON CONFLICT DO NOTHING.

Usage:
    python -m src.ingestors.regulations_seeder
"""

import logging
import os

import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# ---------------------------------------------------------------------------
# Regulation definitions
# Populate pokemon_names with real Pokédex names from the pokemon table.
# This is a placeholder — replace pokemon_names with the real regulation list.
# ---------------------------------------------------------------------------

REGULATIONS = [
    {
        "name": "Example Regulation",
        "description": "Placeholder regulation for development and testing. Replace with real VGC regulation data.",
        "pokemon_names": [
            "bulbasaur", "ivysaur", "venusaur",
            "charmander", "charmeleon", "charizard",
            "squirtle", "wartortle", "blastoise",
        ],
    },
]


def _get_pokemon_ids(cursor, names: list[str]) -> dict[str, int]:
    """Resolve pokemon names to ids, logging any names not found in the DB.

    Args:
        cursor: Active psycopg2 cursor.
        names: List of pokemon names (case-insensitive).

    Returns:
        Dict mapping lowercase name to pokemon id for all found names.
    """
    if not names:
        return {}
    placeholders = ",".join(["%s"] * len(names))
    cursor.execute(
        f"SELECT id, LOWER(name) FROM pokemon WHERE LOWER(name) IN ({placeholders})",
        [n.lower() for n in names],
    )
    found = {row[1]: row[0] for row in cursor.fetchall()}
    unknown = [n for n in names if n.lower() not in found]
    if unknown:
        logger.warning("Unknown Pokémon names (skipped): %s", ", ".join(unknown))
    return found


def seed_regulations(cursor) -> None:
    """Insert all REGULATIONS definitions idempotently.

    Args:
        cursor: Active psycopg2 cursor.
    """
    for reg in REGULATIONS:
        cursor.execute(
            """
            INSERT INTO regulations (name, description)
            VALUES (%s, %s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id
            """,
            (reg["name"], reg["description"]),
        )
        row = cursor.fetchone()
        if row is None:
            cursor.execute(
                "SELECT id FROM regulations WHERE name = %s", (reg["name"],)
            )
            row = cursor.fetchone()
        regulation_id = row[0]

        name_to_id = _get_pokemon_ids(cursor, reg["pokemon_names"])
        if name_to_id:
            execute_values(
                cursor,
                """
                INSERT INTO regulation_pokemon (regulation_id, pokemon_id)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                [(regulation_id, pid) for pid in name_to_id.values()],
            )
        logger.info(
            "Seeded regulation '%s' (id=%d) with %d Pokémon.",
            reg["name"], regulation_id, len(name_to_id),
        )


def main() -> None:
    """Connect to the DB and seed all regulations."""
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )
    try:
        with conn, conn.cursor() as cursor:
            seed_regulations(cursor)
        logger.info("Regulation seeding complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
