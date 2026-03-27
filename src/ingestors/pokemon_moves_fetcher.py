# src/pokemon_moves_fetcher.py
"""Fetch Pokémon moves from PokeAPI and store them in the database.

Three tables are populated:
- `move_categories` (id, name) - already populated with physical/special/status
- `moves` (id, name, type_id, power, accuracy, pp, category_id, effect)
- `pokemon_moves` (pokemon_id, move_id, learn_method, level)

The design mirrors other fetchers in the project.
"""

import os
import re
import time
import logging
from typing import Optional, Tuple, List, Dict

import requests
import psycopg2
from psycopg2.extras import execute_values
from concurrent.futures import ThreadPoolExecutor, as_completed

# Global HTTP session for connection pooling
session = requests.Session()

# Logging configuration
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database credentials
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# Category mapping
CATEGORY_MAP = {
    "physical": 1,
    "special": 2,
    "status": 3,
}


def _request_with_retry(url: str, retries: int = 3, backoff: float = 1.0) -> Optional[requests.Response]:
    """GET with retry & rate-limit handling."""
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, timeout=10)
            if response.status_code == 429:
                logger.warning("Rate limited by PokeAPI, sleeping... (attempt %s)", attempt)
                time.sleep(backoff)
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            logger.error("Request error for %s: %s (attempt %s)", url, exc, attempt)
            time.sleep(backoff)
    logger.error("Failed to fetch %s after %s attempts", url, retries)
    return None


def _get_all_move_urls() -> List[str]:
    """Return list of URLs for every move."""
    url = "https://pokeapi.co/api/v2/move?limit=1000"
    resp = _request_with_retry(url)
    if not resp:
        return []
    data = resp.json()
    return [entry["url"] for entry in data.get("results", [])]


def _extract_pokemon_id(pokemon_url: str) -> Optional[int]:
    """Extract Pokemon ID from URL."""
    match = re.search(r"/pokemon/(\d+)/?", pokemon_url)
    return int(match.group(1)) if match else None


def _extract_type_id(type_url: str) -> Optional[int]:
    """Extract type ID from URL."""
    match = re.search(r"/type/(\d+)/?", type_url)
    return int(match.group(1)) if match else None


def _get_english_effect_text(effect_entries: List[Dict]) -> Optional[str]:
    """Extract English effect text from effect entries."""
    for entry in effect_entries:
        if entry.get("language", {}).get("name") == "en":
            text = entry.get("effect", "")
            # Clean up the text
            text = text.replace("\n", " ").strip()
            return text
    return None


# Global cache for Pokemon moves data to avoid duplicate API calls
_pokemon_moves_cache: Dict[int, List[Dict]] = {}


def _fetch_pokemon_moves(pokemon_id: int) -> Optional[List[Dict]]:
    """Fetch the moves array from the Pokemon endpoint.
    
    Returns the full 'moves' array which contains move entries with
    version_group_details including level_learned_at and move_learn_method.
    Uses cache to avoid duplicate API calls.
    """
    # Check cache first
    if pokemon_id in _pokemon_moves_cache:
        return _pokemon_moves_cache[pokemon_id]
    
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}/"
    resp = _request_with_retry(url)
    if not resp:
        return None
    
    data = resp.json()
    moves_list = data.get("moves", [])
    
    # Cache the result
    _pokemon_moves_cache[pokemon_id] = moves_list
    return moves_list


def _transform_move_detail(detail_url: str) -> Optional[Tuple]:
    """Transform a move detail endpoint into DB rows.
    
    Returns: (move_row, list_of_pokemon_move_rows)
    """
    resp = _request_with_retry(detail_url)
    if not resp:
        return None
    data = resp.json()
    
    # Basic move fields
    move_id = data.get("id")
    name = data.get("name")
    
    if not (move_id and name):
        logger.warning("Missing id or name for move %s", detail_url)
        return None
    
    # Get type_id from type URL
    type_url = data.get("type", {}).get("url")
    type_id = _extract_type_id(type_url) if type_url else None
    
    if not type_id:
        logger.warning("Missing type_id for move %s", name)
        return None
    
    # Get category_id from damage class
    damage_class = data.get("damage_class", {}).get("name")
    category_id = CATEGORY_MAP.get(damage_class)
    
    if not category_id:
        logger.warning("Unknown damage class '%s' for move %s", damage_class, name)
        # Default to status if unknown
        category_id = 3
    
    # Stats
    power = data.get("power")
    accuracy = data.get("accuracy")
    pp = data.get("pp")
    
    # Effect text
    effect = _get_english_effect_text(data.get("effect_entries", []))
    
    # Move row
    move_row = (move_id, name, type_id, power, accuracy, pp, category_id, effect)
    
    # Extract pokemon_moves relationships
    pokemon_moves_rows = []
    
    # Get learned_by_pokemon list
    learned_by = data.get("learned_by_pokemon", [])
    
    for pokemon_entry in learned_by:
        pokemon_url = pokemon_entry.get("url")
        pokemon_id = _extract_pokemon_id(pokemon_url) if pokemon_url else None
        
        if not pokemon_id or pokemon_id >= 10000:
            # Skip non-base pokemon forms
            continue
        
        # Fetch the Pokemon's full move list to get version_group_details
        # which contains level_learned_at and move_learn_method
        moves_list = _fetch_pokemon_moves(pokemon_id)
        if not moves_list:
            logger.warning("Could not fetch moves for Pokemon %s", pokemon_id)
            continue
        
        # Find the move entry that matches the current move
        # First try matching by move URL
        move_url = f"https://pokeapi.co/api/v2/move/{move_id}/"
        matching = next(
            (m for m in moves_list if m.get("move", {}).get("url") == move_url),
            None
        )
        
        # If not found by URL, try matching by move name
        if not matching:
            matching = next(
                (m for m in moves_list if m.get("move", {}).get("name") == name),
                None
            )
        
        if not matching:
            logger.debug("Move %s (%s) not found in Pokemon %s moves list", 
                        move_id, name, pokemon_id)
            continue
        
        # Extract version_group_details with learn method and level
        version_group_details = matching.get("version_group_details", [])
        
        for detail in version_group_details:
            learn_method = detail.get("move_learn_method", {}).get("name")
            level_learned = detail.get("level_learned_at")
            
            if learn_method:
                pokemon_moves_rows.append((
                    pokemon_id,
                    move_id,
                    learn_method,
                    level_learned if level_learned and level_learned > 0 else None
                ))
    
    return move_row, pokemon_moves_rows


def fetch_and_store_moves():
    """Main entry point - fetch all moves and store them."""
    logger.info("Fetching list of move URLs from PokeAPI")
    move_urls = _get_all_move_urls()
    logger.info("Found %s move URLs", len(move_urls))
    
    # Clear cache before starting new fetch
    global _pokemon_moves_cache
    _pokemon_moves_cache = {}
    
    moves_rows: List[Tuple] = []
    pokemon_moves_rows: List[Tuple] = []
    
    # Parallel fetch of move details
    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_url = {executor.submit(_transform_move_detail, url): url for url in move_urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
            except Exception as exc:
                logger.error("Error processing move %s: %s", url, exc)
                continue
            
            if not result:
                logger.warning("Skipping move at %s due to missing data", url)
                continue
            
            move_row, pm_rows = result
            moves_rows.append(move_row)
            pokemon_moves_rows.extend(pm_rows)
    
    # Deduplicate pokemon_moves_rows to avoid ON CONFLICT errors
    # Keep only unique (pokemon_id, move_id, learn_method) combinations
    # For duplicates, keep the first occurrence (with the level from first version group)
    seen = set()
    deduplicated_rows = []
    for row in pokemon_moves_rows:
        key = (row[0], row[1], row[2])  # (pokemon_id, move_id, learn_method)
        if key not in seen:
            seen.add(key)
            deduplicated_rows.append(row)
    pokemon_moves_rows = deduplicated_rows
    logger.info("Deduplicated to %s unique pokemon-move relationships", len(pokemon_moves_rows))
    
    if not moves_rows:
        logger.error("No moves data to insert - aborting")
        return
    
    # Insert moves
    moves_sql = """
        INSERT INTO moves (id, name, type_id, power, accuracy, pp, category_id, effect)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            type_id = EXCLUDED.type_id,
            power = EXCLUDED.power,
            accuracy = EXCLUDED.accuracy,
            pp = EXCLUDED.pp,
            category_id = EXCLUDED.category_id,
            effect = EXCLUDED.effect;
    """
    
    # Insert pokemon_moves
    pm_sql = """
        INSERT INTO pokemon_moves (pokemon_id, move_id, learn_method, level)
        VALUES %s
        ON CONFLICT (pokemon_id, move_id, learn_method) DO UPDATE SET
            level = EXCLUDED.level;
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
                # Insert moves
                execute_values(cur, moves_sql, moves_rows)
                logger.info("Inserted/updated %s moves", len(moves_rows))
                
                # Insert pokemon_moves in batches
                batch_size = 500
                for i in range(0, len(pokemon_moves_rows), batch_size):
                    batch = pokemon_moves_rows[i:i + batch_size]
                    execute_values(cur, pm_sql, batch)
                
                logger.info("Inserted/updated %s pokemon-move relationships", len(pokemon_moves_rows))
                
    except Exception as exc:
        logger.exception("Database insertion failed: %s", exc)


if __name__ == "__main__":
    fetch_and_store_moves()
