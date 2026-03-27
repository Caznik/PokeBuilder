# src/ingestors/type_effectiveness_seeder.py
"""Seed the type_effectiveness table with Pokemon type matchup data.

This script populates the type_effectiveness table with the full Pokemon
type effectiveness chart. It queries the types table to get name->id mappings,
then inserts all relationships from the TYPE_CHART constant.

Usage:
    python -m src.ingestors.type_effectiveness_seeder

Note: This script performs a clean install (no ON CONFLICT handling).
Run it once on a fresh database or after manually clearing the table.
"""

import os
import logging
from typing import Dict, List, Tuple

import psycopg2
from psycopg2.extras import execute_values

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database credentials
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# Type effectiveness chart (attacker -> defender -> multiplier)
TYPE_CHART = {
    "normal": {
        "rock": 0.5, "ghost": 0.0, "steel": 0.5
    },
    "fire": {
        "fire": 0.5, "water": 0.5, "grass": 2.0, "ice": 2.0,
        "bug": 2.0, "rock": 0.5, "dragon": 0.5, "steel": 2.0
    },
    "water": {
        "fire": 2.0, "water": 0.5, "grass": 0.5,
        "ground": 2.0, "rock": 2.0, "dragon": 0.5
    },
    "electric": {
        "water": 2.0, "electric": 0.5, "grass": 0.5,
        "ground": 0.0, "flying": 2.0, "dragon": 0.5
    },
    "grass": {
        "fire": 0.5, "water": 2.0, "grass": 0.5,
        "poison": 0.5, "ground": 2.0, "flying": 0.5,
        "bug": 0.5, "rock": 2.0, "dragon": 0.5, "steel": 0.5
    },
    "ice": {
        "fire": 0.5, "water": 0.5, "grass": 2.0,
        "ice": 0.5, "ground": 2.0, "flying": 2.0,
        "dragon": 2.0, "steel": 0.5
    },
    "fighting": {
        "normal": 2.0, "ice": 2.0, "poison": 0.5,
        "flying": 0.5, "psychic": 0.5, "bug": 0.5,
        "rock": 2.0, "ghost": 0.0, "dark": 2.0,
        "steel": 2.0, "fairy": 0.5
    },
    "poison": {
        "grass": 2.0, "poison": 0.5, "ground": 0.5,
        "rock": 0.5, "ghost": 0.5, "steel": 0.0,
        "fairy": 2.0
    },
    "ground": {
        "fire": 2.0, "electric": 2.0, "grass": 0.5,
        "poison": 2.0, "flying": 0.0, "bug": 0.5,
        "rock": 2.0, "steel": 2.0
    },
    "flying": {
        "electric": 0.5, "grass": 2.0, "fighting": 2.0,
        "bug": 2.0, "rock": 0.5, "steel": 0.5
    },
    "psychic": {
        "fighting": 2.0, "poison": 2.0, "psychic": 0.5,
        "dark": 0.0, "steel": 0.5
    },
    "bug": {
        "fire": 0.5, "grass": 2.0, "fighting": 0.5,
        "poison": 0.5, "flying": 0.5, "psychic": 2.0,
        "ghost": 0.5, "dark": 2.0, "steel": 0.5,
        "fairy": 0.5
    },
    "rock": {
        "fire": 2.0, "ice": 2.0, "fighting": 0.5,
        "ground": 0.5, "flying": 2.0, "bug": 2.0,
        "steel": 0.5
    },
    "ghost": {
        "normal": 0.0, "psychic": 2.0,
        "ghost": 2.0, "dark": 0.5
    },
    "dragon": {
        "dragon": 2.0, "steel": 0.5, "fairy": 0.0
    },
    "dark": {
        "fighting": 0.5, "psychic": 2.0,
        "ghost": 2.0, "dark": 0.5, "fairy": 0.5
    },
    "steel": {
        "fire": 0.5, "water": 0.5, "electric": 0.5,
        "ice": 2.0, "rock": 2.0, "steel": 0.5,
        "fairy": 2.0
    },
    "fairy": {
        "fire": 0.5, "fighting": 2.0, "poison": 0.5,
        "dragon": 2.0, "dark": 2.0, "steel": 0.5
    }
}


def get_type_name_to_id_map(cursor) -> Dict[str, int]:
    """Build a mapping of type names to IDs."""
    cursor.execute("SELECT id, name FROM types")
    return {row[1].lower(): row[0] for row in cursor.fetchall()}


def generate_effectiveness_rows(type_map: Dict[str, int]) -> List[Tuple[int, int, float]]:
    """Convert TYPE_CHART into database rows with type IDs."""
    rows = []
    
    for attacker_name, defenders in TYPE_CHART.items():
        attacker_id = type_map.get(attacker_name.lower())
        if attacker_id is None:
            logger.warning(f"Unknown attacker type: {attacker_name}")
            continue
        
        for defender_name, multiplier in defenders.items():
            defender_id = type_map.get(defender_name.lower())
            if defender_id is None:
                logger.warning(f"Unknown defender type: {defender_name}")
                continue
            
            rows.append((attacker_id, defender_id, float(multiplier)))
    
    return rows


def seed_type_effectiveness():
    """Main entry point to seed the type_effectiveness table."""
    logger.info("Starting type effectiveness seeding...")
    
    try:
        with psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        ) as conn:
            with conn.cursor() as cur:
                # Get type name to ID mapping
                logger.info("Fetching type mappings from database...")
                type_map = get_type_name_to_id_map(cur)
                
                if not type_map:
                    logger.error("No types found in database. Run pokemon_types_fetcher first.")
                    return
                
                logger.info(f"Found {len(type_map)} types")
                
                # Generate effectiveness rows
                rows = generate_effectiveness_rows(type_map)
                logger.info(f"Generated {len(rows)} effectiveness relationships")
                
                if not rows:
                    logger.error("No rows to insert. Aborting.")
                    return
                
                # Insert all rows
                insert_sql = """
                    INSERT INTO type_effectiveness (attacker_type_id, defender_type_id, multiplier)
                    VALUES %s
                """
                execute_values(cur, insert_sql, rows)
                
                logger.info(f"Successfully inserted {len(rows)} type effectiveness rows")
                
    except psycopg2.Error as e:
        logger.exception(f"Database error during seeding: {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    seed_type_effectiveness()
