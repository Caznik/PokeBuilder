# src/api/services/regulation_service.py
"""CRUD operations and pool-filter helpers for VGC regulations."""

from typing import Any

from psycopg2.extras import execute_values


def get_regulation_info(conn: Any, regulation_id: int) -> tuple[str, set[str]]:
    """Return the regulation name and its allowed Pokémon names.

    Args:
        conn: Active psycopg2 connection.
        regulation_id: DB id of the regulation.

    Returns:
        Tuple of (regulation_name, set_of_lowercase_pokemon_names).

    Raises:
        ValueError: If no regulation with this id exists.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT name FROM regulations WHERE id = %s", (regulation_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError(f"regulation {regulation_id} does not exist")
        regulation_name = row[0]
        cur.execute(
            """
            SELECT p.name
            FROM regulation_pokemon rp
            JOIN pokemon p ON rp.pokemon_id = p.id
            WHERE rp.regulation_id = %s
            """,
            (regulation_id,),
        )
        allowed = {r[0].lower() for r in cur.fetchall()}
    return regulation_name, allowed


def get_allowed_names(conn: Any, regulation_id: int) -> set[str]:
    """Return the set of lowercase Pokémon names allowed under a regulation.

    Args:
        conn: Active psycopg2 connection.
        regulation_id: DB id of the regulation.

    Returns:
        Set of lowercase pokemon names.

    Raises:
        ValueError: If no regulation with this id exists.
    """
    _, allowed = get_regulation_info(conn, regulation_id)
    return allowed


def list_regulations(cursor: Any) -> list[dict]:
    """Return all regulations as a list of dicts.

    Args:
        cursor: Active psycopg2 cursor.

    Returns:
        List of dicts with keys: id, name, description.
    """
    cursor.execute("SELECT id, name, description FROM regulations ORDER BY id")
    return [{"id": r[0], "name": r[1], "description": r[2]} for r in cursor.fetchall()]


def get_regulation(cursor: Any, regulation_id: int) -> dict:
    """Return a regulation with its full allowed Pokémon list.

    Args:
        cursor: Active psycopg2 cursor.
        regulation_id: DB id of the regulation.

    Returns:
        Dict with keys: id, name, description, pokemon (list[str]).

    Raises:
        ValueError: If no regulation with this id exists.
    """
    cursor.execute(
        "SELECT id, name, description FROM regulations WHERE id = %s",
        (regulation_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"regulation {regulation_id} not found")
    reg_id, name, description = row

    cursor.execute(
        """
        SELECT p.name
        FROM regulation_pokemon rp
        JOIN pokemon p ON rp.pokemon_id = p.id
        WHERE rp.regulation_id = %s
        ORDER BY p.name
        """,
        (regulation_id,),
    )
    pokemon = [r[0] for r in cursor.fetchall()]
    return {"id": reg_id, "name": name, "description": description, "pokemon": pokemon}


def _resolve_pokemon_ids(cursor: Any, pokemon_names: list[str]) -> list[int]:
    """Resolve Pokémon names to DB ids, raising ValueError for any unknown names.

    Args:
        cursor: Active psycopg2 cursor.
        pokemon_names: List of names to resolve (case-insensitive).

    Returns:
        List of pokemon ids in the same order as pokemon_names.

    Raises:
        ValueError: If any names are not found in the pokemon table.
    """
    if not pokemon_names:
        return []
    placeholders = ",".join(["%s"] * len(pokemon_names))
    cursor.execute(
        f"SELECT id, LOWER(name) FROM pokemon WHERE LOWER(name) IN ({placeholders})",
        [n.lower() for n in pokemon_names],
    )
    found = {row[1]: row[0] for row in cursor.fetchall()}
    unknown = [n for n in pokemon_names if n.lower() not in found]
    if unknown:
        raise ValueError(f"unknown Pokémon names: {', '.join(unknown)}")
    return [found[n.lower()] for n in pokemon_names]


def create_regulation(
    cursor: Any,
    name: str,
    description: str | None,
    pokemon_names: list[str],
) -> dict:
    """Create a new regulation with the given allowed Pokémon.

    Args:
        cursor: Active psycopg2 cursor.
        name: Unique regulation name.
        description: Optional description text.
        pokemon_names: Pokémon names to allow; all must exist in the DB.

    Returns:
        Created regulation dict with keys: id, name, description, pokemon.

    Raises:
        ValueError: If any pokemon_name is not found in the DB.
        ValueError: If a regulation with this name already exists.
    """
    cursor.execute(
        "SELECT id FROM regulations WHERE LOWER(name) = LOWER(%s)", (name,)
    )
    if cursor.fetchone():
        raise ValueError(f"regulation '{name}' already exists")

    pokemon_ids = _resolve_pokemon_ids(cursor, pokemon_names)

    cursor.execute(
        "INSERT INTO regulations (name, description) VALUES (%s, %s) RETURNING id",
        (name, description),
    )
    regulation_id = cursor.fetchone()[0]

    if pokemon_ids:
        execute_values(
            cursor,
            "INSERT INTO regulation_pokemon (regulation_id, pokemon_id) VALUES %s"
            " ON CONFLICT DO NOTHING",
            [(regulation_id, pid) for pid in pokemon_ids],
        )

    return get_regulation(cursor, regulation_id)


def update_regulation(
    cursor: Any,
    regulation_id: int,
    name: str | None,
    description: str | None,
    pokemon_names: list[str] | None,
) -> dict:
    """Update a regulation's name, description, and/or Pokémon list.

    If pokemon_names is provided, the existing allowlist is fully replaced.

    Args:
        cursor: Active psycopg2 cursor.
        regulation_id: DB id of the regulation to update.
        name: New name (None = no change).
        description: New description (None = no change).
        pokemon_names: New full pokemon list (None = no change; replaces if provided).

    Returns:
        Updated regulation dict.

    Raises:
        ValueError: If regulation not found.
        ValueError: If any pokemon_name is unknown.
    """
    cursor.execute("SELECT id FROM regulations WHERE id = %s", (regulation_id,))
    if not cursor.fetchone():
        raise ValueError(f"regulation {regulation_id} not found")

    if name is not None:
        cursor.execute(
            "UPDATE regulations SET name = %s WHERE id = %s", (name, regulation_id)
        )
    if description is not None:
        cursor.execute(
            "UPDATE regulations SET description = %s WHERE id = %s",
            (description, regulation_id),
        )
    if pokemon_names is not None:
        pokemon_ids = _resolve_pokemon_ids(cursor, pokemon_names)
        cursor.execute(
            "DELETE FROM regulation_pokemon WHERE regulation_id = %s", (regulation_id,)
        )
        if pokemon_ids:
            execute_values(
                cursor,
                "INSERT INTO regulation_pokemon (regulation_id, pokemon_id) VALUES %s",
                [(regulation_id, pid) for pid in pokemon_ids],
            )

    return get_regulation(cursor, regulation_id)


def delete_regulation(cursor: Any, regulation_id: int) -> None:
    """Delete a regulation and its associated pokemon rows (cascaded).

    Args:
        cursor: Active psycopg2 cursor.
        regulation_id: DB id of the regulation to delete.

    Raises:
        ValueError: If no regulation with this id exists.
    """
    cursor.execute("SELECT id FROM regulations WHERE id = %s", (regulation_id,))
    if not cursor.fetchone():
        raise ValueError(f"regulation {regulation_id} not found")
    cursor.execute("DELETE FROM regulations WHERE id = %s", (regulation_id,))
