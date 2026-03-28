# src/api/services/stat_service.py
"""Stat calculation service with IVs, EVs, and Nature modifiers."""

from typing import Dict, Optional
from psycopg2.extensions import connection


# Stat field names (matches Pokemon model)
STATS = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]


def _validate_evs(evs: Dict[str, int]) -> None:
    """Validate EV constraints."""
    total = sum(evs.values())
    if total > 510:
        raise ValueError(f"Total EVs ({total}) may not exceed 510")
    for val in evs.values():
        if not 0 <= val <= 252:
            raise ValueError("Each EV must be between 0 and 252")


def _validate_ivs(ivs: Dict[str, int]) -> None:
    """Validate IV constraints."""
    for val in ivs.values():
        if not 0 <= val <= 31:
            raise ValueError("Each IV must be between 0 and 31")


def _get_nature_modifier(nature: Dict[str, Optional[str]], stat: str) -> float:
    """Get nature multiplier for a stat."""
    inc = nature.get("increased_stat")
    dec = nature.get("decreased_stat")
    if inc == stat:
        return 1.1
    if dec == stat:
        return 0.9
    return 1.0


def _calc_hp(base: int, iv: int, ev: int, level: int) -> int:
    """Calculate HP stat."""
    # HP = ((2 * Base + IV + EV/4) * Level / 100) + Level + 10
    return ((2 * base + iv + ev // 4) * level // 100) + level + 10


def _calc_other(base: int, iv: int, ev: int, level: int, nature_mult: float) -> int:
    """Calculate other stat (attack, defense, etc.)."""
    # Stat = (((2 * Base + IV + EV/4) * Level / 100) + 5) * Nature
    return int((((2 * base + iv + ev // 4) * level // 100) + 5) * nature_mult)


def calculate_stats(
    conn: connection,
    pokemon_name: str,
    level: int,
    nature_name: str,
    evs: Dict[str, int],
    ivs: Dict[str, int],
) -> Dict[str, int]:
    """Calculate final stats for a Pokemon.
    
    Args:
        conn: Database connection
        pokemon_name: Pokemon name (case-insensitive)
        level: Pokemon level (1-100)
        nature_name: Nature name (case-insensitive)
        evs: EV distribution (defaults to 0 for omitted stats)
        ivs: IV distribution (defaults to 31 for omitted stats)
    
    Returns:
        Dictionary of final stats
        
    Raises:
        ValueError: If validation fails or Pokemon/Nature not found
    """
    # Validate inputs
    _validate_evs(evs)
    _validate_ivs(ivs)
    
    # Fetch base stats
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT base_hp, base_attack, base_defense,
                   base_sp_attack, base_sp_defense, base_speed
            FROM pokemon
            WHERE LOWER(name) = LOWER(%s)
            """,
            (pokemon_name,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Pokemon '{pokemon_name}' not found")
    
    base_stats = {
        "hp": row[0],
        "attack": row[1],
        "defense": row[2],
        "sp_attack": row[3],
        "sp_defense": row[4],
        "speed": row[5],
    }
    
    # Fetch nature
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT increased_stat, decreased_stat
            FROM natures
            WHERE LOWER(name) = LOWER(%s)
            """,
            (nature_name,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"Nature '{nature_name}' not found")
    
    nature = {
        "increased_stat": row[0],
        "decreased_stat": row[1],
    }
    
    # Apply defaults: EVs = 0, IVs = 31
    evs = {stat: evs.get(stat, 0) for stat in STATS}
    ivs = {stat: ivs.get(stat, 31) for stat in STATS}
    
    # Calculate final stats
    result = {}
    for stat in STATS:
        base = base_stats[stat]
        ev = evs[stat]
        iv = ivs[stat]
        
        if stat == "hp":
            result[stat] = _calc_hp(base, iv, ev, level)
        else:
            nature_mult = _get_nature_modifier(nature, stat)
            result[stat] = _calc_other(base, iv, ev, level, nature_mult)
    
    return result
