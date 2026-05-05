# src/ingestors/regulation_m_a_fetcher.py
"""Ingestor for VGC Regulation M-A — scrapes the Serebii allowed-Pokémon list.

Usage:
    python -m src.ingestors.regulation_m_a_fetcher
"""

import logging
import os
import re
import unicodedata

import psycopg2
import requests
from bs4 import BeautifulSoup
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REGULATION_NAME = "Regulation M-A"
REGULATION_DESC = "VGC Regulation M-A — allowed Pokémon list scraped from Serebii."
SEREBII_URL = "https://www.serebii.net/pokemonchampions/rankedbattle/regulationm-a.shtml"

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def normalize_name(raw: str) -> str:
    """Normalize a Pokémon display name to match the pokemon table name convention.

    Args:
        raw: Display name from Serebii (e.g. "Nidoran♀", "Mr. Mime", "Flabébé").

    Returns:
        Normalized lowercase hyphenated name (e.g. "nidoran-f", "mr-mime", "flabebe").
    """
    name = raw.replace("♀", "-f").replace("♂", "-m")
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = name.lower()
    name = name.replace("'", "").replace(".", "").replace(":", "")
    name = re.sub(r"[^a-z0-9 \-]", "", name)
    name = name.replace(" ", "-")
    name = re.sub(r"-{2,}", "-", name)
    return name.strip("-")


def parse_pokemon_names(html: str) -> list[str]:
    """Extract and normalize Pokémon names from a Serebii regulation page.

    Looks for all anchor tags linking to a Pokédex page and reads the alt
    text of the contained image. Adjust the selector here if the Serebii
    page structure changes.

    Args:
        html: Raw HTML of the Serebii regulation page.

    Returns:
        Deduplicated list of normalized Pokémon names in page order.
    """
    soup = BeautifulSoup(html, "html.parser")
    names: list[str] = []
    for link in soup.select("a[href*='/pokedex-champions/']"):
        href = link.get("href", "")
        m = re.match(r"/pokedex-champions/([^/.]+)/$", href)
        if m:
            names.append(m.group(1))
    return list(dict.fromkeys(names))


def fetch_pokemon_names(url: str = SEREBII_URL) -> list[str]:
    """Fetch and parse the Regulation M-A Pokémon list from Serebii.

    Args:
        url: Serebii URL for the regulation page.

    Returns:
        List of normalized Pokémon names.

    Raises:
        requests.HTTPError: If the HTTP request returns a non-2xx status.
    """
    response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return parse_pokemon_names(response.text)


def _get_pokemon_ids(cursor, names: list[str]) -> dict[str, int]:
    """Resolve Pokémon names to DB ids, logging any unmatched names.

    Args:
        cursor: Active psycopg2 cursor.
        names: List of normalized Pokémon names.

    Returns:
        Dict mapping name to pokemon.id for all matched names.
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


def seed(cursor, pokemon_names: list[str]) -> None:
    """Insert Regulation M-A and its Pokémon allowlist idempotently.

    Args:
        cursor: Active psycopg2 cursor.
        pokemon_names: Normalized Pokémon names to associate with the regulation.
    """
    cursor.execute(
        """
        INSERT INTO regulations (name, description)
        VALUES (%s, %s)
        ON CONFLICT (name) DO NOTHING
        RETURNING id
        """,
        (REGULATION_NAME, REGULATION_DESC),
    )
    row = cursor.fetchone()
    if row is None:
        cursor.execute(
            "SELECT id FROM regulations WHERE name = %s", (REGULATION_NAME,)
        )
        row = cursor.fetchone()
    regulation_id = row[0]

    name_to_id = _get_pokemon_ids(cursor, pokemon_names)
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
        "Seeded '%s' (id=%d) with %d Pokémon.",
        REGULATION_NAME, regulation_id, len(name_to_id),
    )


def main() -> None:
    """Fetch Regulation M-A from Serebii and seed it into the database."""
    pokemon_names = fetch_pokemon_names()
    logger.info("Fetched %d Pokémon names from Serebii.", len(pokemon_names))
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )
    try:
        with conn, conn.cursor() as cursor:
            seed(cursor, pokemon_names)
        logger.info("Regulation M-A seeding complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
