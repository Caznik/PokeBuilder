# src/pokemon_fetcher.py

"""Pokemon data fetcher and storage service.

This module provides a function `fetch_and_store()` that retrieves all Pokémon from the
public PokeAPI, extracts the fields required by the `pokemon` SQL table and inserts
them into a PostgreSQL database.

The implementation follows the design described in `workflows/workflow-pokemon_fetch/SPEC.md`.
"""

import os
import re
import time
import logging
from typing import Tuple, Optional

import requests
import psycopg2
from psycopg2.extras import execute_values
from concurrent.futures import ThreadPoolExecutor, as_completed

# Create a reusable HTTP session for connection pooling
session = requests.Session()



# Configure basic logging
logging.basicConfig(level=logging.DEBUG)  # always show debug logs
logger = logging.getLogger(__name__)

# Database connection parameters – derived from docker-compose.yml
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# Mapping from PokeAPI stat names to our DB column order
STAT_NAME_MAP = {
    "hp": "base_hp",
    "attack": "base_attack",
    "defense": "base_defense",
    "special-attack": "base_sp_attack",
    "special-defense": "base_sp_defense",
    "speed": "base_speed",
}

def _parse_generation(generation_name: str) -> Optional[int]:
    """Parse a generation string like "generation-ix" → 9.
    Returns ``None`` if parsing fails.
    """
    match = re.search(r"generation-(\w+)", generation_name)
    if not match:
        return None
    roman = match.group(1).lower()
    roman_map = {
        "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5,
        "vi": 6, "vii": 7, "viii": 8, "ix": 9,
    }
    return roman_map.get(roman)

# Deprecated static generation map – kept only for backward compatibility.
GENERATION_MAP = {
    "generation-i": 1,
    "generation-ii": 2,
    "generation-iii": 3,
    "generation-iv": 4,
    "generation-v": 5,
    "generation-vi": 6,
    "generation-vii": 7,
    "generation-viii": 8,
}


def _request_with_retry(url: str, retries: int = 3, backoff: float = 1.0) -> Optional[requests.Response]:
    """Perform an HTTP GET with retry on rate‑limit (429) and transient errors.

    Args:
        url: URL to request.
        retries: Number of attempts.
        backoff: Seconds to wait between attempts.

    Returns:
        ``requests.Response`` if successful, otherwise ``None``.
    """
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=5)
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


def _extract_generation(generation_url: str) -> Optional[int]:
    """Fetch generation data and convert to integer.

    Returns ``None`` if the generation cannot be determined.
    """
    resp = _request_with_retry(generation_url)
    if not resp:
        return None
    data = resp.json()
    name = data.get("name")
    return GENERATION_MAP.get(name)


def _transform_pokemon_detail(detail_url: str) -> Optional[Tuple]:
    """Transform a Pokémon detail endpoint into a DB row.

    Returns ``None`` when required data is missing.
    """
    resp = _request_with_retry(detail_url)
    if not resp:
        return None
    data = resp.json()

    # Basic fields
    pokemon_id = data.get("id")
    name = data.get("name")
    if not (pokemon_id and name):
        logger.warning("Missing id or name for %s", detail_url)
        return None

    # Stats extraction
    stats = {entry["stat"]["name"]: entry["base_stat"] for entry in data.get("stats", [])}
    # Verify all required stats are present
    try:
        base_hp = stats["hp"]
        base_attack = stats["attack"]
        base_defense = stats["defense"]
        base_sp_attack = stats["special-attack"]
        base_sp_defense = stats["special-defense"]
        base_speed = stats["speed"]
    except KeyError as missing:
        logger.warning("Missing stat %s for Pokémon %s", missing, name)
        return None

    # Generation – secondary request
    species_url = data.get("species", {}).get("url")
    generation = None
    if species_url:
        species_resp = _request_with_retry(species_url)
        if species_resp:
            species_data = species_resp.json()
            gen_name = species_data.get("generation", {}).get("name")
            generation = _parse_generation(gen_name) if gen_name else None

    return (
        pokemon_id,
        name,
        generation,
        base_hp,
        base_attack,
        base_defense,
        base_sp_attack,
        base_sp_defense,
        base_speed,
    )


def _get_all_pokemon_urls() -> list:
    """Retrieve the list of all Pokémon URLs from the API.

    Returns an empty list on failure.
    """
    url = "https://pokeapi.co/api/v2/pokemon?limit=10000"
    resp = _request_with_retry(url)
    if not resp:
        return []
    data = resp.json()
    return [entry["url"] for entry in data.get("results", [])]


def fetch_and_store():
    """Main entry point – fetch all Pokémon and store them in the DB.

    The function is idempotent; running it multiple times will not duplicate rows.
    """
    logger.info("Fetching list of Pokémon URLs from PokeAPI")
    pokemon_urls = _get_all_pokemon_urls()
    logger.info("Found %s Pokémon URLs", len(pokemon_urls))

    rows = []
    # Use a ThreadPoolExecutor to fetch Pokémon details in parallel (concurrency ~ 20 workers)
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_url = {executor.submit(_transform_pokemon_detail, url): url for url in pokemon_urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                row = future.result()
            except Exception as exc:
                logger.error("Error processing %s: %s", url, exc)
                continue
            if row:
                rows.append(row)
            else:
                logger.warning("Skipping Pokémon at %s due to missing data", url)

    if not rows:
        logger.error("No Pokémon data to insert – aborting")
        return

    # Insert into PostgreSQL in batches of 100 rows to avoid huge memory usage
    insert_sql = """
        INSERT INTO pokemon (
            id, name, generation,
            base_hp, base_attack, base_defense,
            base_sp_attack, base_sp_defense, base_speed
        ) VALUES %s
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
                cur.execute("SELECT 1")
                batch_size = 100
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i+batch_size]
                    execute_values(cur, insert_sql, batch)
        logger.info("Inserted %s Pokémon rows in %d batches", len(rows), (len(rows) + batch_size - 1) // batch_size)
    except Exception as exc:
        logger.exception("Database insertion failed: %s", exc)


if __name__ == "__main__":
    fetch_and_store()

