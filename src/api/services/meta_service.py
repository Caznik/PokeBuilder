# src/api/services/meta_service.py
"""Meta profiling service — usage statistics and win rates from battle replay data."""

from typing import Any


def get_meta_snapshot(conn: Any, regulation_id: int, top_n: int = 10) -> dict:
    """Compute usage statistics for the current meta.

    Args:
        conn: Active psycopg2 connection.
        regulation_id: Regulation to analyze.
        top_n: Number of top Pokémon to return.

    Returns:
        Dict with keys top_pokemon (list of {name, usage_pct}) and
        total_battles (int). usage_pct is relative to total team slots
        (total_battles × 2, since both teams are counted).
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM battle_replays WHERE regulation_id = %s",
            (regulation_id,),
        )
        total: int = cur.fetchone()[0]
        if total == 0:
            return {"top_pokemon": [], "total_battles": 0}

        cur.execute(
            """
            SELECT unnest(team) AS pokemon, COUNT(*) AS n
            FROM battle_teams bt
            JOIN battle_replays br ON br.id = bt.replay_id
            WHERE br.regulation_id = %s
            GROUP BY pokemon
            ORDER BY n DESC
            LIMIT %s
            """,
            (regulation_id, top_n),
        )
        top_pokemon = [
            {"name": row[0], "usage_pct": round(row[1] / (total * 2), 3)}
            for row in cur.fetchall()
        ]
    return {"top_pokemon": top_pokemon, "total_battles": total}


def get_battle_matchups(conn: Any, regulation_id: int) -> list[dict]:
    """Load all (winning_team, losing_team) pairs for a regulation.

    Args:
        conn: Active psycopg2 connection.
        regulation_id: Regulation to analyze.

    Returns:
        List of dicts with keys winner (list[str]) and loser (list[str]),
        where each list is the 6-Pokémon team composition.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT bt_w.team, bt_l.team
            FROM battle_replays br
            JOIN battle_teams bt_w
                ON bt_w.replay_id = br.id AND bt_w.player = br.winner
            JOIN battle_teams bt_l
                ON bt_l.replay_id = br.id AND bt_l.player != br.winner
            WHERE br.regulation_id = %s
            """,
            (regulation_id,),
        )
        return [{"winner": list(row[0]), "loser": list(row[1])} for row in cur.fetchall()]


def compute_win_rates(
    matchups: list[dict],
    meta_pokemon: set[str],
) -> dict[str, float]:
    """Compute per-Pokémon win rate against meta opponents.

    A meta matchup is any battle where the losing team contains at least
    one Pokémon from meta_pokemon. For each Pokémon P:
    - appearances = battles (in meta matchups) where P was on either team
    - wins = battles (in meta matchups) where P was on the winning team
    - win_rate = wins / appearances

    Args:
        matchups: List of {winner: list[str], loser: list[str]} dicts.
        meta_pokemon: Names of Pokémon considered "meta".

    Returns:
        Dict mapping pokemon_name → win_rate (float in [0.0, 1.0]).
        Only includes Pokémon that appeared in at least one meta matchup.
    """
    meta_matchups = [m for m in matchups if meta_pokemon & set(m["loser"])]
    if not meta_matchups:
        return {}

    wins: dict[str, int] = {}
    appearances: dict[str, int] = {}

    for m in meta_matchups:
        for p in m["winner"]:
            wins[p] = wins.get(p, 0) + 1
            appearances[p] = appearances.get(p, 0) + 1
        for p in m["loser"]:
            appearances[p] = appearances.get(p, 0) + 1

    return {p: wins.get(p, 0) / appearances[p] for p in appearances}
