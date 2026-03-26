# src/pokemon_abilities_fetcher.py

"""Fetch Pokémon abilities from PokeAPI and store them in the database.

Two tables are populated:
- `abilities` (id, name)
- `pokemon_abilities` (pokemon_id, ability_id, is_hidden)

The design mirrors `src/pokemon_fetcher.py` but adds the many‑to‑many relationship.
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

# Global HTTP session for connection pooling
session = requests.Session()

# Logging – DEBUG for development, can be switched to INFO for production
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# DB credentials – read from environment (fallback to dev defaults)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def _request_with_retry(url: str, retries: int = 3, backoff: float = 1.0) -> Optional[requests.Response]:
    """GET with simple retry & 429 handling (same logic as other fetchers)."""
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


def _get_all_ability_urls() -> List[str]:
    """Return a list of URLs for every ability.
    PokeAPI endpoint: /api/v2/ability?limit=1000 (covers all current abilities).
    """
    url = "https://pokeapi.co/api/v2/ability?limit=1000"
    resp = _request_with_retry(url)
    if not resp:
        return []
    data = resp.json()
    return [entry["url"] for entry in data.get("results", [])]


def _extract_pokemon_id(pokemon_url: str) -> Optional[int]:
    # Made the trailing slash optional with ?
    match = re.search(r"/pokemon/(\d+)/?", pokemon_url)
    return int(match.group(1)) if match else None

def _transform_ability_detail(detail_url: str) -> Optional[Tuple]:
    resp = _request_with_retry(detail_url)
    if not resp:
        return None
    data = resp.json()

    ability_id = data.get("id")
    name = data.get("name")
    
    # --- Extraction of the English Description ---
    description = None
    
    # 1. Check effect_changes first as requested
    # Note: effect_changes is a list of changes across versions
    changes = data.get("effect_changes", [])
    if changes:
        # We usually want the most recent or any valid English entry
        for change in changes:
            for entry in change.get("effect_entries", []):
                if entry.get("language", {}).get("name") == "en":
                    description = entry.get("effect")
                    break
            if description: break

    # 2. Fallback to the standard effect_entries if no change was found
    if not description:
        for entry in data.get("effect_entries", []):
            if entry.get("language", {}).get("name") == "en":
                description = entry.get("effect")
                break

    # Clean up the text (remove newlines if needed)
    if description:
        description = description.replace("\n", " ").strip()
    else:
        description = "No description available."

    # --- Ability Row now includes the description ---
    ability_row = (ability_id, name, description)
    
    # --- Junction Table Links ---
    links = []
    for entry in data.get("pokemon", []):
        p_url = entry.get("pokemon", {}).get("url")
        p_id = _extract_pokemon_id(p_url)
        # Standardize to only base pokemon (optional filter)
        if p_id and p_id < 10000:
            links.append((p_id, ability_id, entry.get("is_hidden", False)))

    return ability_row, links


def fetch_and_store_abilities():
    """Main entry point – fetch all abilities and store them.
    The operation is idempotent (ON CONFLICT DO NOTHING).
    """
    logger.info("Fetching list of ability URLs from PokeAPI")
    ability_urls = _get_all_ability_urls()
    logger.info("Found %s ability URLs", len(ability_urls))

    abilities_rows: List[Tuple[int, str]] = []
    ability_links: List[Tuple[int, int, bool]] = []

    # Parallel fetch of ability details (≈15 workers is sufficient)
    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_url = {executor.submit(_transform_ability_detail, url): url for url in ability_urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
            except Exception as exc:
                logger.error("Error processing ability %s: %s", url, exc)
                continue
            if not result:
                logger.warning("Skipping ability at %s due to missing data", url)
                continue
            ability_row, links = result
            abilities_rows.append(ability_row)
            ability_links.extend(links)

    if not abilities_rows:
        logger.error("No abilities data to insert – aborting")
        return

    # Insert abilities
    ability_sql = """
        INSERT INTO abilities (id, name, description) 
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET 
            description = EXCLUDED.description;
    """
    # Insert junction rows in batches of 200
    link_sql = """
        INSERT INTO pokemon_abilities (pokemon_id, ability_id, is_hidden) VALUES %s
        ON CONFLICT (pokemon_id, ability_id) DO NOTHING;
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
                # Insert abilities (few rows, single batch)
                execute_values(cur, ability_sql, abilities_rows)
                # Insert links in batches to keep memory low
                batch_size = 200
                for i in range(0, len(ability_links), batch_size):
                    batch = ability_links[i:i + batch_size]
                    execute_values(cur, link_sql, batch)
        logger.info(
            "Inserted %s abilities and %s ability‑pokemon links",
            len(abilities_rows),
            len(ability_links),
        )
    except Exception as exc:
        logger.exception("Database insertion failed: %s", exc)


if __name__ == "__main__":
    fetch_and_store_abilities()