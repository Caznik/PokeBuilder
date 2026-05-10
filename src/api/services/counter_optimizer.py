# src/api/services/counter_optimizer.py
"""Beam-search counter team suggester using battle replay data."""

import logging
from typing import Any

from .meta_service import compute_win_rates, get_battle_matchups, get_meta_snapshot
from .team_generator import PoolEntry, _base_species, _build_pool, _is_acceptable
from .team_loader import load_build
from .team_analysis import analyze_team
from .team_scorer import score_team
from . import regulation_service

_LOG = logging.getLogger(__name__)

BEAM_WIDTH = 20
META_TOP_N = 10
MAX_RESULTS_COUNTER = 5
TEAM_SIZE = 6
MIN_META_BATTLES = 10


def _score_partial(
    partial: list[tuple[str, int]],
    win_rates: dict[str, float],
) -> float:
    """Score a partial team as the mean win rate of its members vs meta.

    Args:
        partial: List of (pokemon_name, set_id) pairs.
        win_rates: Pre-computed per-pokemon win rates vs meta opponents.

    Returns:
        Mean win rate (0.0 if no data or empty partial).
    """
    if not partial:
        return 0.0
    rates = [win_rates.get(name, 0.0) for name, _ in partial]
    return sum(rates) / len(rates)


def suggest_counter_team(
    conn: Any,
    regulation_id: int,
    beam_width: int = BEAM_WIDTH,
    meta_top_n: int = META_TOP_N,
) -> dict:
    """Suggest teams empirically proven to counter the current meta.

    Seeds the beam with the top-beam_width Pokémon by win rate, then
    greedily extends each candidate by one slot per step, always keeping
    the top beam_width partial teams.

    Args:
        conn: Active psycopg2 connection.
        regulation_id: Regulation to analyze and counter.
        beam_width: Beam width (max partial teams retained at each step).
        meta_top_n: Number of meta Pokémon used to define the meta.

    Returns:
        Dict with keys best_teams, algorithm, meta_snapshot, replays_analyzed.

    Raises:
        ValueError: If fewer than MIN_META_BATTLES replays exist for this
            regulation, or if the pool is empty.
    """
    meta = get_meta_snapshot(conn, regulation_id, top_n=meta_top_n)
    if meta["total_battles"] < MIN_META_BATTLES:
        raise ValueError(
            f"Not enough battle data for regulation {regulation_id}: "
            f"need {MIN_META_BATTLES}, have {meta['total_battles']}"
        )

    meta_pokemon = {p["name"] for p in meta["top_pokemon"]}
    matchups = get_battle_matchups(conn, regulation_id)
    win_rates = compute_win_rates(matchups, meta_pokemon)

    regulation_name, allowed = regulation_service.get_regulation_info(conn, regulation_id)
    format_filter = "VGC" if "vgc" in regulation_name.lower() else None
    pool = _build_pool(conn, format_filter=format_filter)
    pool = [e for e in pool if e.pokemon_name.lower() in allowed]

    if not pool:
        raise ValueError(f"No pool entries for regulation {regulation_id}")

    # Seed beam: top-beam_width entries by win rate to avoid O(pool²) first step
    sorted_entries = sorted(pool, key=lambda e: win_rates.get(e.pokemon_name, 0.0), reverse=True)
    beam: list[list[tuple[str, int]]] = [
        [(e.pokemon_name, e.set_id)] for e in sorted_entries[:beam_width]
    ]

    for _step in range(TEAM_SIZE - 1):
        candidates: list[tuple[list[tuple[str, int]], float]] = []
        for partial in beam:
            taken_bases = {_base_species(n) for n, _ in partial}
            for entry in pool:
                if _base_species(entry.pokemon_name) in taken_bases:
                    continue
                extended = partial + [(entry.pokemon_name, entry.set_id)]
                candidates.append((extended, _score_partial(extended, win_rates)))

        candidates.sort(key=lambda x: x[1], reverse=True)
        seen: set[frozenset] = set()
        beam = []
        for partial, _ in candidates:
            key = frozenset(partial)
            if key not in seen:
                seen.add(key)
                beam.append(partial)
                if len(beam) >= beam_width:
                    break

    pool_by_key = {(e.pokemon_name, e.set_id): e for e in pool}
    best_teams = []
    for chromosome in beam:
        builds = [load_build(conn, name, sid) for name, sid in chromosome]
        report = analyze_team(builds)
        if not _is_acceptable(report):
            continue
        scoring = score_team(report, builds)
        members = []
        for (name, sid), build in zip(chromosome, builds):
            entry = pool_by_key.get((name, sid))
            members.append({
                "pokemon_name": name,
                "set_id": sid,
                "set_name": entry.set_name if entry else None,
                "nature": build.nature,
                "ability": build.ability,
            })
        best_teams.append({
            "score": scoring["score"],
            "breakdown": scoring["breakdown"],
            "members": members,
            "analysis": report,
        })
        if len(best_teams) >= MAX_RESULTS_COUNTER:
            break

    return {
        "best_teams": best_teams,
        "algorithm": "beam_search",
        "meta_snapshot": meta,
        "replays_analyzed": meta["total_battles"],
    }
