# src/ingestors/vgc_sets_fetcher.py
"""VGC competitive sets ingestor — scrapes Pikalytics and stores sets in the DB.

Usage:
    python -m src.ingestors.vgc_sets_fetcher                         # fetch list, store all
    python -m src.ingestors.vgc_sets_fetcher garchomp                 # single Pokémon
    python -m src.ingestors.vgc_sets_fetcher --regulation "VGC 2025 Reg G"
"""

import logging
import os
import re
from typing import Optional

import psycopg2
import requests
from bs4 import BeautifulSoup, NavigableString

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

DEFAULT_REGULATION_SLUG = "sv-vgc-2025-reg-g"
DEFAULT_REGULATION_NAME = "VGC 2025 Reg G"
PIKALYTICS_BASE = "https://pikalytics.com/pokedex"
SET_NAME = "Pikalytics Usage"
REQUEST_TIMEOUT = 15
USER_AGENT = "PokeBuilder/1.0 (educational project)"
MIN_MOVES = 4
# PokeAPI appends these suffixes for default forms; Pikalytics omits them.
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

EV_STAT_MAP = {
    "HP": "hp",
    "Atk": "attack",
    "Def": "defense",
    "SpA": "sp_attack",
    "SpD": "sp_defense",
    "Spe": "speed",
}

session = requests.Session()
session.headers["User-Agent"] = USER_AGENT


# ---------------------------------------------------------------------------
# Name normalization and DB helpers
# ---------------------------------------------------------------------------

def _to_pikalytics_slug(db_name: str) -> str:
    """Translate a PokeAPI DB name to its Pikalytics URL slug.

    Strips default-form suffixes that PokeAPI appends but Pikalytics omits
    (e.g. '-breed', '-incarnate', '-standard'). Regional forms are preserved.

    Args:
        db_name: Pokémon name as stored in the DB (PokeAPI format).

    Returns:
        Pikalytics-compatible slug.
    """
    for suffix in _DEFAULT_FORM_SUFFIXES:
        if db_name.endswith(suffix):
            return db_name[: -len(suffix)]
    return db_name


def _normalize(name: str) -> str:
    """Normalize a display name to PokeAPI-style lowercase-hyphenated form.

    Args:
        name: Raw display name (e.g. "Flutter Mane", "Mr. Mime").

    Returns:
        Normalized slug (e.g. "flutter-mane", "mr-mime").
    """
    name = name.lower().strip()
    name = re.sub(r"['\.]", "", name)
    name = re.sub(r"[\s\-]+", "-", name)
    return name.strip("-")


def _lookup_id(cursor, table: str, name_col: str, name: str) -> Optional[int]:
    """Look up a row ID by normalized name.

    Args:
        cursor: Active psycopg2 cursor.
        table: Table name to query.
        name_col: Column containing the name.
        name: Name to look up (compared case-insensitively).

    Returns:
        Integer ID if found, else None.
    """
    cursor.execute(
        f"SELECT id FROM {table} WHERE LOWER({name_col}) = %s",  # noqa: S608
        (name.lower(),),
    )
    row = cursor.fetchone()
    return row[0] if row else None


# ---------------------------------------------------------------------------
# EV spread parsing
# ---------------------------------------------------------------------------

def _parse_ev_spread(spread: str) -> dict:
    """Parse a Pikalytics EV spread string into a DB-ready dict.

    Args:
        spread: String like "252 Atk / 4 Def / 252 Spe" (may be empty).

    Returns:
        Dict with keys hp, attack, defense, sp_attack, sp_defense, speed;
        all values default to 0.
    """
    evs = {col: 0 for col in EV_STAT_MAP.values()}
    if not spread:
        return evs
    for part in spread.split("/"):
        part = part.strip()
        tokens = part.split()
        if len(tokens) < 2:
            continue
        try:
            value = int(tokens[0])
        except ValueError:
            continue
        abbr = tokens[1]
        col = EV_STAT_MAP.get(abbr)
        if col:
            evs[col] = value
    return evs


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _get_first_text(tag) -> str:
    """Return the first bare NavigableString child of a tag, stripped.

    Args:
        tag: A BeautifulSoup tag whose first text node is the label.

    Returns:
        Stripped text string, or empty string if none found.
    """
    for child in tag.children:
        if isinstance(child, NavigableString) and child.strip():
            return child.strip()
    return ""


# ---------------------------------------------------------------------------
# Pikalytics fetching
# ---------------------------------------------------------------------------

def _get_regulation_pokemon(conn, regulation_name: str) -> list[str]:
    """Return all Pokémon names allowed under a regulation from the DB.

    Uses the regulation_pokemon table, which is populated by the regulation
    ingestors and holds the authoritative full allowlist.

    Args:
        conn: Active psycopg2 connection.
        regulation_name: Exact regulation name as stored in the DB.

    Returns:
        List of lowercase Pokémon names, or empty list if regulation not found.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.name
            FROM pokemon p
            JOIN regulation_pokemon rp ON rp.pokemon_id = p.id
            JOIN regulations r ON r.id = rp.regulation_id
            WHERE LOWER(r.name) = LOWER(%s)
            ORDER BY p.name
            """,
            (regulation_name,),
        )
        return [row[0] for row in cur.fetchall()]


def _parse_pokemon_page(html: str) -> dict:
    """Parse a Pikalytics individual Pokémon page.

    Locates each section via <p class="pika-static"> headers and extracts
    the top-ranked entry for moves, ability, item, nature, and EV spread.

    Args:
        html: Raw HTML of the Pokémon's Pikalytics page.

    Returns:
        Dict with keys: moves (list[str]), ability (str), item (str),
        nature (str), ev_spread (str). Missing sections default to empty.
    """
    soup = BeautifulSoup(html, "html.parser")
    result: dict = {"moves": [], "ability": "", "item": "", "nature": "", "ev_spread": ""}

    for header in soup.find_all("p", class_="pika-static"):
        label = header.get_text().strip()
        parent = header.parent
        items = parent.find_all("div", recursive=False)
        if not items:
            continue

        if "Top Moves" in label:
            result["moves"] = [
                _get_first_text(d)
                for d in items[:MIN_MOVES]
                if _get_first_text(d)
            ]
        elif "Top Abilities" in label:
            result["ability"] = _get_first_text(items[0])
        elif "Top Items" in label:
            result["item"] = _get_first_text(items[0])
        elif "Top Natures" in label:
            result["nature"] = _get_first_text(items[0])
        elif "Top EV Spreads" in label:
            result["ev_spread"] = _get_first_text(items[0])

    return result


def _fetch_url(url: str) -> Optional[str]:
    """GET a URL and return response text, or None on HTTP error.

    Args:
        url: Full URL to fetch.

    Returns:
        Response text on success, None on any requests error.
    """
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        logger.error("HTTP error fetching %s: %s", url, exc)
        return None


def _fetch_pokemon_page(pokemon_slug: str, regulation_slug: str) -> Optional[dict]:
    """Fetch and parse an individual Pokémon's Pikalytics page.

    Tries the base slug first, then falls back to the -mega variant for
    Pokémon whose competitive page is listed under their Mega Evolution.

    Args:
        pokemon_slug: Normalized Pokémon name (query params stripped).
        regulation_slug: Regulation URL slug.

    Returns:
        Parsed page dict, or None if both attempts fail.
    """
    clean_slug = _to_pikalytics_slug(pokemon_slug.split("?")[0].strip("/"))
    base_url = f"{PIKALYTICS_BASE}/{regulation_slug}/{clean_slug}"
    html = _fetch_url(base_url)
    if html is None:
        mega_url = f"{PIKALYTICS_BASE}/{regulation_slug}/{clean_slug}-mega"
        logger.info("Retrying with mega slug: %s", mega_url)
        html = _fetch_url(mega_url)
    if html is None:
        return None
    return _parse_pokemon_page(html)


# ---------------------------------------------------------------------------
# DB persistence
# ---------------------------------------------------------------------------

def _insert_set_details(cur, set_id: int, page_data: dict) -> None:
    """Insert EVs and moves for a newly created competitive set.

    Args:
        cur: Active psycopg2 cursor.
        set_id: ID of the competitive_sets row.
        page_data: Parsed page dict with ev_spread and moves keys.
    """
    evs = _parse_ev_spread(page_data.get("ev_spread", ""))
    cur.execute(
        """
        INSERT INTO competitive_set_evs
            (set_id, hp, attack, defense, sp_attack, sp_defense, speed)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (set_id) DO NOTHING
        """,
        (set_id, evs["hp"], evs["attack"], evs["defense"],
         evs["sp_attack"], evs["sp_defense"], evs["speed"]),
    )
    for move_name in (page_data.get("moves") or [])[:MIN_MOVES]:
        move_norm = _normalize(move_name)
        move_id = _lookup_id(cur, "moves", "name", move_norm)
        if move_id is None:
            logger.warning("Move '%s' not in DB — skipping", move_norm)
            continue
        cur.execute(
            "INSERT INTO competitive_set_moves (set_id, move_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (set_id, move_id),
        )


def _store_vgc_set(conn, pokemon_name: str, page_data: dict, regulation_name: str) -> bool:
    """Persist one VGC competitive set for a Pokémon.

    Deletes any existing VGC format sets for the Pokémon before inserting.

    Args:
        conn: Active psycopg2 connection.
        pokemon_name: PokeAPI-format Pokémon name.
        page_data: Parsed page dict from _parse_pokemon_page.
        regulation_name: Format label stored in competitive_sets.format.

    Returns:
        True if the set was stored, False if the Pokémon was not found in DB.
    """
    with conn.cursor() as cur:
        pokemon_id = _lookup_id(cur, "pokemon", "name", pokemon_name)
        if pokemon_id is None:
            logger.warning("Pokemon '%s' not in DB — skipping", pokemon_name)
            return False

        cur.execute(
            "DELETE FROM competitive_sets WHERE pokemon_id = %s AND LOWER(format) = LOWER(%s)",
            (pokemon_id, regulation_name),
        )

        nature_id = _lookup_id(cur, "natures", "name", page_data.get("nature", "")) if page_data.get("nature") else None
        ability_norm = _normalize(page_data.get("ability", ""))
        ability_id = _lookup_id(cur, "abilities", "name", ability_norm) if ability_norm else None

        cur.execute(
            """
            INSERT INTO competitive_sets (pokemon_id, name, nature_id, ability_id, item, format)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (pokemon_id, SET_NAME, nature_id, ability_id, page_data.get("item"), regulation_name),
        )
        set_id = cur.fetchone()[0]
        _insert_set_details(cur, set_id, page_data)

    conn.commit()
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_and_store(pokemon_name: str, regulation_slug: str, regulation_name: str) -> bool:
    """Fetch and store one Pokémon's VGC set from Pikalytics.

    Args:
        pokemon_name: PokeAPI-format Pokémon name used as the URL slug.
        regulation_slug: Pikalytics regulation URL slug.
        regulation_name: Human-readable regulation label for the DB.

    Returns:
        True if the set was successfully stored.
    """
    logger.info("Fetching VGC set for %s", pokemon_name)
    page_data = _fetch_pokemon_page(pokemon_name, regulation_slug)
    if page_data is None:
        return False

    with psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    ) as conn:
        return _store_vgc_set(conn, pokemon_name, page_data, regulation_name)


def fetch_and_store_all(
    pokemon_names: list[str], regulation_slug: str, regulation_name: str
) -> dict[str, bool]:
    """Batch-fetch VGC sets for multiple Pokémon.

    Args:
        pokemon_names: List of PokeAPI-format Pokémon names.
        regulation_slug: Pikalytics regulation URL slug.
        regulation_name: Human-readable regulation label for the DB.

    Returns:
        Dict mapping pokemon_name to True (stored) or False (failed/skipped).
    """
    results: dict[str, bool] = {}
    for name in pokemon_names:
        try:
            results[name] = fetch_and_store(name, regulation_slug, regulation_name)
        except Exception as exc:
            logger.error("Failed to process %s: %s", name, exc)
            results[name] = False
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch VGC sets from Pikalytics")
    parser.add_argument("pokemon", nargs="?", default=None, help="Single Pokémon name")
    parser.add_argument("--regulation", default=DEFAULT_REGULATION_NAME, help="Regulation label")
    parser.add_argument("--slug", default=DEFAULT_REGULATION_SLUG, help="Pikalytics URL slug")
    args = parser.parse_args()

    if args.pokemon:
        success = fetch_and_store(args.pokemon, args.slug, args.regulation)
        print(f"{'Stored' if success else 'Skipped'} set for {args.pokemon}")
    else:
        with psycopg2.connect(
            host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
            user=DB_USER, password=DB_PASSWORD,
        ) as conn:
            names = _get_regulation_pokemon(conn, args.regulation)
        if not names:
            print(f"No Pokémon found for regulation '{args.regulation}' in DB. Check the name.")
        else:
            results = fetch_and_store_all(names, args.slug, args.regulation)
            stored = sum(1 for v in results.values() if v)
            print(f"Done. Stored sets for {stored}/{len(names)} Pokémon.")
