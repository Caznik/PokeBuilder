# src/api/services/type_service.py
"""Type effectiveness service with in-memory matrix caching.

This module provides O(1) lookups for Pokemon type effectiveness multipliers.
The full type effectiveness matrix is loaded from the database once at import time
and cached in memory for the lifetime of the process.

Example usage:
    >>> from src.api.services import calculate_damage_multiplier
    >>> 
    >>> # Fire vs Grass = 2.0
    >>> calculate_damage_multiplier("fire", "grass")
    2.0
    >>> 
    >>> # Fire vs Grass/Steel = 4.0
    >>> calculate_damage_multiplier("fire", ["grass", "steel"])
    4.0
    >>> 
    >>> # Get all multipliers against a dual-type Pokemon
    >>> all_multipliers_against(["grass", "steel"])
    {'normal': 1.0, 'fire': 4.0, 'water': 0.5, ...}

The matrix is loaded lazily on first use via _ensure_loaded().
"""

from typing import Dict, List, Sequence, Tuple, Union
import os
import logging
import psycopg2

logger = logging.getLogger(__name__)

# Database credentials
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "pokebuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# In-memory cache (loaded once)
_matrix: Dict[Tuple[int, int], float] = {}
_name_to_id: Dict[str, int] = {}
_id_to_name: Dict[int, str] = {}
_is_loaded: bool = False


def _ensure_loaded():
    """Ensure the type matrix is loaded from the database."""
    global _is_loaded, _matrix, _name_to_id, _id_to_name
    
    if _is_loaded:
        return
    
    _matrix = {}
    _name_to_id = {}
    _id_to_name = {}
    
    try:
        with psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        ) as conn:
            with conn.cursor() as cur:
                # Load type name mappings
                cur.execute("SELECT id, name FROM types")
                for row in cur.fetchall():
                    type_id = row[0]
                    type_name = row[1].lower()
                    _name_to_id[type_name] = type_id
                    _id_to_name[type_id] = type_name
                
                logger.info(f"Loaded {len(_name_to_id)} types")
                
                # Load type effectiveness matrix
                cur.execute("""
                    SELECT attacker_type_id, defender_type_id, multiplier
                    FROM type_effectiveness
                """)
                for row in cur.fetchall():
                    attacker_id = row[0]
                    defender_id = row[1]
                    multiplier = float(row[2])
                    _matrix[(attacker_id, defender_id)] = multiplier
                
                logger.info(f"Loaded {len(_matrix)} type effectiveness relationships")
                
    except psycopg2.Error as e:
        logger.error(f"Failed to load type matrix: {e}")
        raise
    
    _is_loaded = True


def get_type_id(name: Union[str, int]) -> int:
    """Resolve a type name to its ID.
    
    Args:
        name: Type name (string) or ID (int). If already an int, returns it.
        
    Returns:
        The type ID.
        
    Raises:
        ValueError: If the type name is not found.
    """
    _ensure_loaded()
    
    if isinstance(name, int):
        return name
    
    type_id = _name_to_id.get(name.lower())
    if type_id is None:
        raise ValueError(f"Unknown type: {name}")
    
    return type_id


def get_type_name(type_id: int) -> str:
    """Resolve a type ID to its name.
    
    Args:
        type_id: The type ID.
        
    Returns:
        The type name.
        
    Raises:
        ValueError: If the type ID is not found.
    """
    _ensure_loaded()
    
    type_name = _id_to_name.get(type_id)
    if type_name is None:
        raise ValueError(f"Unknown type ID: {type_id}")
    
    return type_name


def get_multiplier(
    move_type: Union[str, int],
    defender_type: Union[str, int]
) -> float:
    """Get the damage multiplier for a single type matchup.
    
    Args:
        move_type: The attacking move's type (name or ID).
        defender_type: The defender's type (name or ID).
        
    Returns:
        The damage multiplier (2.0, 1.0, 0.5, or 0.0).
        Missing relationships default to 1.0 (neutral).
    """
    _ensure_loaded()
    
    attacker_id = get_type_id(move_type)
    defender_id = get_type_id(defender_type)
    
    return _matrix.get((attacker_id, defender_id), 1.0)


def calculate_damage_multiplier(
    move_type: Union[str, int],
    defender_types: Sequence[Union[str, int]]
) -> float:
    """Calculate the final damage multiplier for a move against a Pokemon.
    
    For dual-type Pokemon, this multiplies the individual type multipliers.
    
    Args:
        move_type: The attacking move's type (name or ID).
        defender_types: The defender's type(s) - single type (string/int) or list.
        
    Returns:
        The final damage multiplier.
        
    Examples:
        >>> calculate_damage_multiplier("fire", "grass")
        2.0
        >>> calculate_damage_multiplier("fire", ["grass", "steel"])
        4.0
        >>> calculate_damage_multiplier("electric", "ground")
        0.0
    """
    # Handle single type passed as string or int
    if isinstance(defender_types, (str, int)):
        defender_types = [defender_types]
    
    multiplier = 1.0
    for defender_type in defender_types:
        m = get_multiplier(move_type, defender_type)
        multiplier *= m
    
    return multiplier


def all_multipliers_against(
    defender_types: Sequence[Union[str, int]]
) -> Dict[str, float]:
    """Get all damage multipliers for all attacking types against a defender.
    
    This is useful for analyzing type coverage and weaknesses.
    
    Args:
        defender_types: The defender's type(s) - single type (string/int) or list.
        
    Returns:
        A dictionary mapping attacker type names to damage multipliers.
        
    Example:
        >>> all_multipliers_against(["grass", "steel"])
        {
            'normal': 0.5,
            'fire': 4.0,
            'water': 0.5,
            'electric': 0.5,
            ...
        }
    """
    _ensure_loaded()
    
    # Ensure we have a sequence
    if isinstance(defender_types, (str, int)):
        defender_types = [defender_types]
    
    result = {}
    for attacker_name, attacker_id in _name_to_id.items():
        multiplier = calculate_damage_multiplier(attacker_id, defender_types)
        result[attacker_name] = multiplier
    
    return result


def get_all_attacker_types() -> List[str]:
    """Get a list of all attacker type names.
    
    Returns:
        A sorted list of all type names.
    """
    _ensure_loaded()
    return sorted(_name_to_id.keys())
