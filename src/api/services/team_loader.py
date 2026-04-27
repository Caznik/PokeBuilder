# src/api/services/team_loader.py
"""Load PokemonBuild instances from the database."""

from typing import Any

from .stat_service import calculate_stats
from ..models.team import MoveDetail, PokemonBuild


def load_build(conn: Any, pokemon_name: str, set_id: int) -> PokemonBuild:
    """Load a single PokemonBuild from the DB and compute its stats.

    Args:
        conn: Active psycopg2 connection.
        pokemon_name: Pokémon name (case-insensitive).
        set_id: ID of the competitive set to load.

    Returns:
        A fully populated PokemonBuild.

    Raises:
        ValueError: If the set_id does not exist for the given Pokémon.
    """
    with conn.cursor() as cur:
        # Load set: EVs, nature, ability, item — verify it belongs to pokemon_name
        cur.execute(
            """
            SELECT
                cs.id, cs.name,
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
            JOIN pokemon p ON cs.pokemon_id = p.id
            LEFT JOIN natures  n   ON cs.nature_id  = n.id
            LEFT JOIN abilities a  ON cs.ability_id = a.id
            LEFT JOIN competitive_set_evs cse ON cs.id = cse.set_id
            WHERE cs.id = %s AND LOWER(p.name) = LOWER(%s)
            """,
            (set_id, pokemon_name),
        )
        row = cur.fetchone()
        if row is None:
            raise ValueError(
                f"Set {set_id} not found for Pokémon '{pokemon_name}'"
            )

        nature  = row[2]
        ability = row[3]
        item    = row[4]
        evs = {
            "hp":         row[5],
            "attack":     row[6],
            "defense":    row[7],
            "sp_attack":  row[8],
            "sp_defense": row[9],
            "speed":      row[10],
        }

        # Load Pokémon types
        cur.execute(
            """
            SELECT t.name
            FROM types t
            JOIN pokemon_types pt ON t.id = pt.type_id
            JOIN pokemon p ON pt.pokemon_id = p.id
            WHERE LOWER(p.name) = LOWER(%s)
            """,
            (pokemon_name,),
        )
        types = [r[0] for r in cur.fetchall()]

        # Load moves with type and damage category
        cur.execute(
            """
            SELECT m.name, t.name AS type, mc.name AS category
            FROM competitive_set_moves csm
            JOIN moves m  ON csm.move_id  = m.id
            JOIN types t  ON m.type_id    = t.id
            JOIN move_categories mc ON m.category_id = mc.id
            WHERE csm.set_id = %s
            ORDER BY m.id
            """,
            (set_id,),
        )
        moves = [MoveDetail(r[0], r[1], r[2]) for r in cur.fetchall()]

    # Compute stats via Sprint 4 engine (uses nature name and EVs from the set)
    stats = calculate_stats(
        conn=conn,
        pokemon_name=pokemon_name,
        level=100,
        nature_name=nature or "hardy",
        evs=evs,
        ivs={},
    )

    return PokemonBuild(
        pokemon_name=pokemon_name,
        set_id=set_id,
        types=types,
        nature=nature,
        ability=ability,
        item=item,
        stats=stats,
        moves=moves,
    )


def load_team(conn: Any, members: list[dict]) -> list[PokemonBuild]:
    """Load a full team of PokemonBuilds from the DB.

    Args:
        conn: Active psycopg2 connection.
        members: List of dicts with keys ``pokemon_name`` and ``set_id``.

    Returns:
        List of PokemonBuild, one per member, in input order.
    """
    return [load_build(conn, m["pokemon_name"], m["set_id"]) for m in members]
