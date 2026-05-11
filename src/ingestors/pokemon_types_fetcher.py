# src/pokemon_types_fetcher.py

"""Fetch Pokémon type data from PokeAPI and store it in the `types` and
`pokemon_types` tables.

The PokeAPI type-detail endpoint already lists every Pokémon that has each
type (with slot number), so a single pass over all type URLs is enough to
populate both tables.

Run AFTER pokemon_fetcher.py so that the `pokemon` table exists and can be
used to skip pokemon we haven't ingested yet (avoiding FK violations).
"""

import os
import time
import logging
from typing import Optional, Tuple, List

import requests
import psycopg2
from psycopg2.extras import execute_values
from concurrent.futures import ThreadPoolExecutor, as_completed

session = requests.Session()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def _request_with_retry(url: str, retries: int = 3, backoff: float = 1.0) -> Optional[requests.Response]:
    """GET with simple retry & rate-limit handling."""
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=10)
            if response.status_code == 429:
                logger.warning("Rate limited by PokeAPI, sleeping… (attempt %s)", attempt)
                time.sleep(backoff)
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            logger.error("Request error for %s: %s (attempt %s)", url, exc, attempt)
            time.sleep(backoff)
    logger.error("Failed to fetch %s after %s attempts", url, retries)
    return None


def _get_all_type_urls() -> List[str]:
    """Return a list of URLs for every Pokémon type."""
    url = "https://pokeapi.co/api/v2/type?limit=1000"
    resp = _request_with_retry(url)
    if not resp:
        return []
    return [entry["url"] for entry in resp.json().get("results", [])]


def _extract_pokemon_id(url: str) -> Optional[int]:
    """Parse a pokemon ID out of a PokeAPI URL like '.../pokemon/16/'."""
    try:
        return int(url.rstrip("/").split("/")[-1])
    except (ValueError, IndexError):
        return None


def _transform_type_detail(url: str) -> Optional[Tuple[int, str, List[Tuple[int, int, int]]]]:
    """Fetch a single type detail.

    Args:
        url: PokeAPI type-detail URL.

    Returns:
        (type_id, type_name, associations) where associations is a list of
        (pokemon_id, type_id, slot) tuples, or None on failure.
    """
    resp = _request_with_retry(url)
    if not resp:
        return None
    data = resp.json()
    type_id = data.get("id")
    name = data.get("name")
    if not (type_id and name):
        logger.warning("Missing id or name for type URL %s", url)
        return None

    associations: List[Tuple[int, int, int]] = []
    for entry in data.get("pokemon", []):
        pokemon_url = entry.get("pokemon", {}).get("url", "")
        slot = entry.get("slot")
        pokemon_id = _extract_pokemon_id(pokemon_url)
        if pokemon_id and slot:
            associations.append((pokemon_id, type_id, slot))

    return (type_id, name, associations)


def fetch_and_store_types():
    """Fetch all types and their pokemon associations, then persist to the DB.

    Idempotent – duplicate inserts are silently ignored.
    Requires the `pokemon` table to be populated first so that FK checks pass.
    """
    logger.info("Fetching list of Pokémon type URLs")
    type_urls = _get_all_type_urls()
    logger.info("Found %s type URLs", len(type_urls))

    type_rows: List[Tuple[int, str]] = []
    all_associations: List[Tuple[int, int, int]] = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(_transform_type_detail, url): url for url in type_urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
            except Exception as exc:
                logger.error("Error processing type %s: %s", url, exc)
                continue
            if result:
                type_id, name, associations = result
                type_rows.append((type_id, name))
                all_associations.extend(associations)
            else:
                logger.warning("Skipping type at %s due to missing data", url)

    if not type_rows:
        logger.error("No type data to insert – aborting")
        return

    try:
        with psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD,
        ) as conn:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    "INSERT INTO types (id, name) VALUES %s ON CONFLICT (id) DO NOTHING",
                    type_rows,
                )
                logger.info("Inserted/verified %s type rows", len(type_rows))

                if all_associations:
                    # Only insert associations for pokemon already in the pokemon table
                    candidate_ids = list({assoc[0] for assoc in all_associations})
                    cur.execute("SELECT id FROM pokemon WHERE id = ANY(%s)", (candidate_ids,))
                    valid_ids = {row[0] for row in cur.fetchall()}

                    valid_associations = [
                        (pid, tid, slot)
                        for pid, tid, slot in all_associations
                        if pid in valid_ids
                    ]
                    if valid_associations:
                        execute_values(
                            cur,
                            "INSERT INTO pokemon_types (pokemon_id, type_id, slot) VALUES %s "
                            "ON CONFLICT (pokemon_id, slot) DO NOTHING",
                            valid_associations,
                        )
                        logger.info(
                            "Inserted/verified %s pokemon_types rows (%s skipped — pokemon not ingested)",
                            len(valid_associations),
                            len(all_associations) - len(valid_associations),
                        )
    except Exception as exc:
        logger.exception("Database insertion failed: %s", exc)


if __name__ == "__main__":
    fetch_and_store_types()
