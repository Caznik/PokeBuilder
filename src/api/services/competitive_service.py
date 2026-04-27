# src/api/services/competitive_service.py
"""Competitive sets service — query stored Smogon sets from the database."""

from typing import Any


def get_sets_for_pokemon(cursor: Any, pokemon_name: str) -> list[dict]:
    """Return all competitive sets for a Pokémon, including EVs and moves.

    Args:
        cursor: Active psycopg2 cursor.
        pokemon_name: Pokémon name (case-insensitive).

    Returns:
        List of set dicts. Empty list if the Pokémon exists but has no sets.

    Raises:
        ValueError: If the Pokémon is not found in the database.
    """
    cursor.execute(
        "SELECT id FROM pokemon WHERE LOWER(name) = LOWER(%s)",
        (pokemon_name,),
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Pokemon '{pokemon_name}' not found")
    pokemon_id = row[0]

    cursor.execute(
        """
        SELECT
            cs.id,
            cs.name,
            n.name  AS nature,
            a.name  AS ability,
            cs.item,
            COALESCE(cse.hp,         0),
            COALESCE(cse.attack,     0),
            COALESCE(cse.defense,    0),
            COALESCE(cse.sp_attack,  0),
            COALESCE(cse.sp_defense, 0),
            COALESCE(cse.speed,      0)
        FROM competitive_sets cs
        LEFT JOIN natures  n   ON cs.nature_id  = n.id
        LEFT JOIN abilities a  ON cs.ability_id = a.id
        LEFT JOIN competitive_set_evs cse ON cs.id = cse.set_id
        WHERE cs.pokemon_id = %s
        ORDER BY cs.id
        """,
        (pokemon_id,),
    )
    set_rows = cursor.fetchall()

    results = []
    for r in set_rows:
        set_id = r[0]

        cursor.execute(
            """
            SELECT m.name
            FROM competitive_set_moves csm
            JOIN moves m ON csm.move_id = m.id
            WHERE csm.set_id = %s
            ORDER BY m.id
            """,
            (set_id,),
        )
        moves = [row[0] for row in cursor.fetchall()]

        results.append({
            "id":       set_id,
            "name":     r[1],
            "nature":   r[2],
            "ability":  r[3],
            "item":     r[4],
            "evs": {
                "hp":         r[5],
                "attack":     r[6],
                "defense":    r[7],
                "sp_attack":  r[8],
                "sp_defense": r[9],
                "speed":      r[10],
            },
            "moves": moves,
        })

    return results
