# src/api/services/battle_log_service.py
"""CRUD service for battle log records."""

from typing import Any

from ..models.battle_log import BattleLogCreate, BattleLogOut

_SELECT_COLUMNS = (
    "bl.id, bl.user_id, bl.saved_team_id, st.name AS saved_team_name, "
    "bl.regulation_id, bl.format, bl.brought_pokemon, bl.enemy_team, bl.enemy_brought, "
    "bl.result, bl.notes, bl.played_at, "
    "ARRAY(SELECT stm.pokemon_name FROM saved_team_members stm "
    "      WHERE stm.team_id = bl.saved_team_id ORDER BY stm.slot) AS saved_team_members"
)

_FROM_JOIN = (
    "FROM battle_logs bl "
    "LEFT JOIN saved_teams st ON bl.saved_team_id = st.id"
)


def _row_to_out(row: tuple) -> BattleLogOut:
    """Map a DB row tuple to a BattleLogOut model.

    Args:
        row: Tuple with columns matching _SELECT_COLUMNS order.

    Returns:
        BattleLogOut populated from the row.
    """
    return BattleLogOut(
        id=row[0],
        user_id=row[1],
        saved_team_id=row[2],
        saved_team_name=row[3],
        regulation_id=row[4],
        format=row[5],
        brought_pokemon=list(row[6]),
        enemy_team=list(row[7]),
        enemy_brought=list(row[8]) if row[8] else [],
        result=row[9],
        notes=row[10],
        played_at=row[11],
        saved_team_members=list(row[12]) if row[12] else [],
    )


def create_log(conn: Any, user_id: int, body: BattleLogCreate) -> BattleLogOut:
    """Insert a new battle log and return the created record.

    Args:
        conn: Active psycopg2 connection.
        user_id: Owner's user id.
        body: Validated BattleLogCreate payload.

    Returns:
        The newly created BattleLogOut.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO battle_logs
                (user_id, saved_team_id, regulation_id, format,
                 brought_pokemon, enemy_team, enemy_brought, result, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                user_id, body.saved_team_id, body.regulation_id, body.format,
                body.brought_pokemon, body.enemy_team, body.enemy_brought, body.result, body.notes,
            ),
        )
        new_id = cur.fetchone()[0]
    conn.commit()

    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {_SELECT_COLUMNS} {_FROM_JOIN} WHERE bl.id = %s",
            (new_id,),
        )
        return _row_to_out(cur.fetchone())


def list_logs(
    conn: Any,
    user_id: int,
    *,
    regulation_id: int | None = None,
    format: str | None = None,
    result: str | None = None,
) -> list[BattleLogOut]:
    """Return battle logs for a user, newest first, with optional filters.

    Args:
        conn: Active psycopg2 connection.
        user_id: Owner's user id.
        regulation_id: Optional regulation FK filter.
        format: Optional format filter ('singles' or 'vgc').
        result: Optional result filter ('win', 'loss', or 'tie').

    Returns:
        List of BattleLogOut, ordered by played_at descending.
    """
    sql = f"SELECT {_SELECT_COLUMNS} {_FROM_JOIN} WHERE bl.user_id = %s"
    params: list[Any] = [user_id]

    if regulation_id is not None:
        sql += " AND bl.regulation_id = %s"
        params.append(regulation_id)
    if format is not None:
        sql += " AND bl.format = %s"
        params.append(format)
    if result is not None:
        sql += " AND bl.result = %s"
        params.append(result)

    sql += " ORDER BY bl.played_at DESC"

    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [_row_to_out(row) for row in cur.fetchall()]


def get_log(conn: Any, log_id: int, user_id: int) -> BattleLogOut:
    """Fetch a single battle log (must belong to user_id).

    Args:
        conn: Active psycopg2 connection.
        log_id: Primary key of the log.
        user_id: Owner's user id.

    Returns:
        BattleLogOut for the requested log.

    Raises:
        ValueError: If the log does not exist or belongs to a different user.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {_SELECT_COLUMNS} {_FROM_JOIN} WHERE bl.id = %s AND bl.user_id = %s",
            (log_id, user_id),
        )
        row = cur.fetchone()
    if row is None:
        raise ValueError(f"Battle log {log_id} not found")
    return _row_to_out(row)


def delete_log(conn: Any, log_id: int, user_id: int) -> None:
    """Delete a battle log owned by user_id.

    Args:
        conn: Active psycopg2 connection.
        log_id: Primary key of the log.
        user_id: Owner's user id.

    Raises:
        ValueError: If the log does not exist or belongs to a different user.
    """
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM battle_logs WHERE id = %s AND user_id = %s",
            (log_id, user_id),
        )
        if cur.rowcount == 0:
            raise ValueError(f"Battle log {log_id} not found")
    conn.commit()
