# src/pokemon_types_fetcher.py

"""Fetch Pokémon type data from PokeAPI and store it in the `types` table.

The table schema (see resources/sql/tables_schemas/types.sql) is:
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE

The script mirrors the design of `pokemon_fetcher.py` but only deals with types.
"""

import os
import re
import time
import logging
from typing import Optional, Tuple, List

import requests
import psycopg2
from psycopg2.extras import execute_values
from concurrent.futures import ThreadPoolExecutor, as_completed

# Re‑use a single requests.Session for connection pooling
session = requests.Session()

# Configure logging – DEBUG for development, can be switched to INFO for prod
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database credentials – read from env with sane defaults (same as pokemon_fetcher)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def _request_with_retry(url: str, retries: int = 3, backoff: float = 1.0) -> Optional[requests.Response]:
    """GET with simple retry & rate‑limit handling (same logic as pokemon_fetcher)."""
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
    """Return a list of URLs for every Pokémon type.
    The PokeAPI endpoint ``/api/v2/type`` lists all types.
    """
    url = "https://pokeapi.co/api/v2/type?limit=1000"
    resp = _request_with_retry(url)
    if not resp:
        return []
    data = resp.json()
    return [entry["url"] for entry in data.get("results", [])]


def _transform_type_detail(url: str) -> Optional[Tuple[int, str]]:
    """Fetch a single type detail and return (id, name)."""
    resp = _request_with_retry(url)
    if not resp:
        return None
    data = resp.json()
    type_id = data.get("id")
    name = data.get("name")
    if not (type_id and name):
        logger.warning("Missing id or name for type URL %s", url)
        return None
    return (type_id, name)


def fetch_and_store_types():
    """Main entry point – fetch all types and insert them into the DB.
    Idempotent – duplicate inserts are ignored via ON CONFLICT.
    """
    logger.info("Fetching list of Pokémon type URLs")
    type_urls = _get_all_type_urls()
    logger.info("Found %s type URLs", len(type_urls))

    rows: List[Tuple[int, str]] = []
    # Parallel fetch – 10 workers is plenty for the small number of types (~20)
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(_transform_type_detail, url): url for url in type_urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                row = future.result()
            except Exception as exc:
                logger.error("Error processing type %s: %s", url, exc)
                continue
            if row:
                rows.append(row)
            else:
                logger.warning("Skipping type at %s due to missing data", url)

    if not rows:
        logger.error("No type data to insert – aborting")
        return

    insert_sql = """
        INSERT INTO types (id, name) VALUES %s
        ON CONFLICT (id) DO NOTHING;
    """
    try:
        with psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        ) as conn:
            with conn.cursor() as cur:
                # Types are few, insert in a single batch
                execute_values(cur, insert_sql, rows)
        logger.info("Inserted %s Pokémon types", len(rows))
    except Exception as exc:
        logger.exception("Database insertion failed: %s", exc)


if __name__ == "__main__":
    fetch_and_store_types()
