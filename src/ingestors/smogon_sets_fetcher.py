# src/ingestors/smogon_sets_fetcher.py
"""Smogon competitive sets ingestor.

Fetches competitive sets from Smogon University dex pages and stores them
in the competitive_sets / competitive_set_moves / competitive_set_evs tables.

Usage:
    python -m src.ingestors.smogon_sets_fetcher garchomp
    python -m src.ingestors.smogon_sets_fetcher  # seeds all Pokemon in DB

Data source: Smogon embeds all dex data as a `dexSettings` JS variable in the page.
The relevant path is:
    dexSettings.injectRpcs[2][1].strategies[*].movesets[*]
Each moveset has: name, abilities[], items[], natures[], moveslots[][], evconfigs[].
"""

import json
import logging
import os
import re
import sys
from typing import Optional

import psycopg2
import requests
from psycopg2.extensions import connection as Connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

SMOGON_GEN = os.getenv("SMOGON_GEN", "sv")
SMOGON_BASE = "https://www.smogon.com/dex"

session = requests.Session()
session.headers["User-Agent"] = "PokeBuilder/1.0 (educational project)"


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------

# PokeAPI names that need explicit remapping to their Smogon URL slug.
# Used for cases where simple suffix stripping gives the wrong result.
_SMOGON_OVERRIDES: dict[str, str] = {
    # Smogon lists Origin Forme as the primary Giratina page
    "giratina-altered": "giratina-origin",
    # Gender variants where Smogon uses the base name (not -male)
    "frillish-male":    "frillish",
    "jellicent-male":   "jellicent",
    "indeedee-male":    "indeedee",
    "basculegion-male": "basculegion",
    "oinkologne-male":  "oinkologne",
}

# PokeAPI appends these suffixes to mark the default form; Smogon omits them.
# Listed longest-first so longer suffixes match before any shorter sub-suffix.
_DEFAULT_FORM_SUFFIXES: tuple[str, ...] = (
    "-family-of-four",
    "-family-of-three",
    "-green-plumage",
    "-yellow-plumage",
    "-white-plumage",
    "-blue-plumage",
    "-single-strike",
    "-full-belly",
    "-two-segment",
    "-red-striped",
    "-incarnate",
    "-ordinary",
    "-disguised",
    "-standard",
    "-midday",
    "-altered",
    "-average",
    "-female",
    "-shield",
    "-normal",
    "-plant",
    "-baile",
    "-breed",
    "-curly",
    "-land",
    "-aria",
    "-solo",
    "-mask",
    "-zero",
    "-ice",
    "-50",
)


def _to_smogon_name(db_name: str) -> str:
    """Translate a PokeAPI-style Pokémon name to its Smogon URL slug.

    PokeAPI appends form suffixes (e.g. '-incarnate', '-standard') that Smogon
    omits. An override dict handles the handful of cases where simple suffix
    stripping would give the wrong slug (e.g. giratina-altered → giratina-origin).

    Args:
        db_name: Pokémon name as stored in the DB (PokeAPI format).

    Returns:
        Smogon-style slug for use in dex page URLs.
    """
    if db_name in _SMOGON_OVERRIDES:
        return _SMOGON_OVERRIDES[db_name]
    for suffix in _DEFAULT_FORM_SUFFIXES:
        if db_name.endswith(suffix):
            return db_name[: -len(suffix)]
    return db_name


def _normalize(name: str) -> str:
    """Normalize a Smogon name to PokeAPI-style lowercase-hyphenated form."""
    name = name.lower().strip()
    name = re.sub(r"['\.]", "", name)       # strip apostrophes, dots
    name = re.sub(r"[\s\-]+", "-", name)    # spaces/dashes → single hyphen
    name = name.strip("-")
    return name


# ---------------------------------------------------------------------------
# Smogon page fetching
# ---------------------------------------------------------------------------

def _fetch_dex_settings(pokemon_name: str) -> Optional[dict]:
    """Fetch and parse the dexSettings JSON object from a Smogon dex page.

    Smogon embeds all data in a JS variable:
        <script>dexSettings = {...};</script>
    We use raw_decode to extract the JSON object without relying on
    a closing sentinel that might not be unique in the page.
    """
    url = f"{SMOGON_BASE}/{SMOGON_GEN}/pokemon/{pokemon_name}/"
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("HTTP error fetching %s: %s", url, exc)
        return None

    marker = "dexSettings = "
    idx = resp.text.find(marker)
    if idx == -1:
        logger.warning("No dexSettings found for %s", pokemon_name)
        return None

    try:
        data, _ = json.JSONDecoder().raw_decode(resp.text, idx + len(marker))
        return data
    except json.JSONDecodeError as exc:
        logger.error("JSON parse error for %s: %s", pokemon_name, exc)
        return None


def _extract_movesets(dex_settings: dict) -> list[dict]:
    """Pull all competitive movesets from the dexSettings structure.

    Structure: dexSettings.injectRpcs[2][1].strategies[*].movesets[*]
    Each moveset is a dict with keys: name, abilities, items, natures,
    moveslots, evconfigs.
    """
    try:
        # injectRpcs[2] is always the dump-pokemon RPC for the current page
        pokemon_data = dex_settings["injectRpcs"][2][1]
        strategies = pokemon_data.get("strategies", [])
    except (KeyError, IndexError, TypeError):
        logger.warning("Unexpected dexSettings structure — no strategies found")
        return []

    movesets = []
    for strategy in strategies:
        for ms in strategy.get("movesets", []):
            movesets.append(ms)
    return movesets


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _lookup_id(cursor, table: str, name_col: str, name: str) -> Optional[int]:
    """Look up a row ID by normalized name. Returns None if not found."""
    cursor.execute(
        f"SELECT id FROM {table} WHERE LOWER({name_col}) = %s",  # noqa: S608
        (name.lower(),),
    )
    row = cursor.fetchone()
    return row[0] if row else None


def _parse_evs(evconfig: dict) -> dict:
    """Map Smogon evconfig field names to our DB column names.

    Smogon uses: hp, atk, def, spa, spd, spe
    """
    return {
        "hp":         evconfig.get("hp",  0) or 0,
        "attack":     evconfig.get("atk", 0) or 0,
        "defense":    evconfig.get("def", 0) or 0,
        "sp_attack":  evconfig.get("spa", 0) or 0,
        "sp_defense": evconfig.get("spd", 0) or 0,
        "speed":      evconfig.get("spe", 0) or 0,
    }


# ---------------------------------------------------------------------------
# Core ingestion
# ---------------------------------------------------------------------------

def _store_movesets(conn: Connection, pokemon_name: str, movesets: list[dict]) -> int:
    """Persist competitive movesets for one Pokémon. Returns number stored."""
    stored = 0
    with conn.cursor() as cur:
        pokemon_id = _lookup_id(cur, "pokemon", "name", pokemon_name)
        if pokemon_id is None:
            logger.warning("Pokemon '%s' not in DB — skipping", pokemon_name)
            return 0

        # Delete existing sets so re-runs replace rather than append (idempotency).
        cur.execute("DELETE FROM competitive_sets WHERE pokemon_id = %s", (pokemon_id,))

        for ms in movesets:
            set_name = ms.get("name")

            # First nature / ability / item in each list
            nature_raw = (ms.get("natures") or [""])[0]
            nature_id = _lookup_id(cur, "natures", "name", nature_raw) if nature_raw else None

            ability_raw = (ms.get("abilities") or [""])[0]
            ability_norm = _normalize(ability_raw) if ability_raw else ""
            ability_id = _lookup_id(cur, "abilities", "name", ability_norm) if ability_norm else None

            item_raw = (ms.get("items") or [None])[0]

            cur.execute(
                """
                INSERT INTO competitive_sets (pokemon_id, name, nature_id, ability_id, item)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (pokemon_id, set_name, nature_id, ability_id, item_raw),
            )
            set_id = cur.fetchone()[0]

            # EVs — use first evconfig if present
            evconfigs = ms.get("evconfigs") or []
            evs = _parse_evs(evconfigs[0]) if evconfigs else _parse_evs({})
            cur.execute(
                """
                INSERT INTO competitive_set_evs
                    (set_id, hp, attack, defense, sp_attack, sp_defense, speed)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (set_id) DO NOTHING
                """,
                (
                    set_id,
                    evs["hp"], evs["attack"], evs["defense"],
                    evs["sp_attack"], evs["sp_defense"], evs["speed"],
                ),
            )

            # Moves — moveslots is a list of slots; each slot is a list of
            # {move, type} dicts. We take the first alternative per slot.
            for slot in ms.get("moveslots") or []:
                if not slot:
                    continue
                move_name_raw = slot[0].get("move", "")
                if not move_name_raw:
                    continue
                move_norm = _normalize(move_name_raw)
                move_id = _lookup_id(cur, "moves", "name", move_norm)
                if move_id is None:
                    logger.warning("Move '%s' not in DB — skipping", move_norm)
                    continue
                cur.execute(
                    """
                    INSERT INTO competitive_set_moves (set_id, move_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (set_id, move_id),
                )

            stored += 1

    conn.commit()
    return stored


def fetch_and_store(pokemon_name: str) -> int:
    """Fetch and persist competitive sets for a single Pokémon.

    Args:
        pokemon_name: Pokémon name as stored in the DB (PokeAPI format).

    Returns:
        Number of sets stored.
    """
    smogon_slug = _to_smogon_name(pokemon_name)
    logger.info("Fetching Smogon sets for %s (slug: %s)", pokemon_name, smogon_slug)
    dex_settings = _fetch_dex_settings(smogon_slug)
    if dex_settings is None:
        return 0

    movesets = _extract_movesets(dex_settings)
    if not movesets:
        logger.info("No competitive sets found for %s", smogon_slug)
        return 0

    logger.info("Found %d sets for %s", len(movesets), smogon_slug)

    with psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    ) as conn:
        return _store_movesets(conn, pokemon_name, movesets)


def fetch_and_store_all(pokemon_names: list[str]) -> dict[str, int]:
    """Batch-fetch competitive sets for multiple Pokémon.

    Args:
        pokemon_names: List of Pokémon names (Smogon URL format).

    Returns:
        Dict mapping pokemon_name → sets stored.
    """
    results = {}
    for name in pokemon_names:
        try:
            results[name] = fetch_and_store(name)
        except Exception as exc:
            logger.error("Failed to process %s: %s", name, exc)
            results[name] = 0
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        count = fetch_and_store(sys.argv[1])
        print(f"Stored {count} sets for {sys.argv[1]}")
    else:
        with psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD,
        ) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name FROM pokemon ORDER BY id")
                names = [row[0] for row in cur.fetchall()]

        totals = fetch_and_store_all(names)
        total_sets = sum(totals.values())
        print(f"Done. Stored {total_sets} sets across {len(names)} Pokémon.")
