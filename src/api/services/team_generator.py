# src/api/services/team_generator.py
"""Guided random team generation engine."""

import random
import re
from typing import Any, NamedTuple

from ..models.generation import GenerationConstraints
from ..models.team import PokemonBuild
from .team_loader import load_build
from .team_analysis import analyze_team
from .role_service import detect_roles
from .team_scorer import score_team, compute_lead_pair_score

MAX_RESULTS = 5
MAX_ITERATIONS = 100
WEAKNESS_THRESHOLD = 3
HEURISTIC_RETRY_BUDGET = 10
MAX_PHYSICAL_ATTACKERS = 2
MAX_SPECIAL_ATTACKERS = 2
MAX_TR_SETTERS = 1

# Matches mega, gmax, and primal form suffixes — these are battle-only
# transformations of the base species and must not share a team slot.
# Regional forms (-alolan, -galarian, etc.) are intentionally excluded:
# they are distinct species with different typings and competitive roles.
_FORM_SUFFIX_RE = re.compile(r'-(mega(-[xy])?|gmax|primal)$', re.IGNORECASE)


def _base_species(name: str) -> str:
    """Return the base species name by stripping mega/gmax/primal suffixes.

    Args:
        name: Pokémon name, possibly including a form suffix.

    Returns:
        Lowercase name with mega/gmax/primal suffix removed.
        Regional forms (alolan, galarian, etc.) are preserved unchanged.
    """
    return _FORM_SUFFIX_RE.sub('', name.lower())


class PoolEntry(NamedTuple):
    pokemon_name: str
    set_id: int
    set_name: str | None
    primary_type: str | None


def _build_pool(conn: Any) -> list[PoolEntry]:
    """Query all competitive sets with their Pokémon name and primary type.

    Args:
        conn: Active psycopg2 connection.

    Returns:
        List of PoolEntry tuples, one per competitive set in the DB.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.name, cs.id, cs.name, t.name AS primary_type
            FROM competitive_sets cs
            JOIN pokemon p ON cs.pokemon_id = p.id
            LEFT JOIN pokemon_types pt ON p.id = pt.pokemon_id AND pt.slot = 1
            LEFT JOIN types t ON pt.type_id = t.id
            ORDER BY p.name, cs.id
            """
        )
        return [PoolEntry(*row) for row in cur.fetchall()]


def _apply_constraints(
    pool: list[PoolEntry],
    constraints: GenerationConstraints,
) -> list[PoolEntry]:
    """Remove excluded Pokémon from the pool.

    Args:
        pool: Full pool of PoolEntry tuples.
        constraints: Constraints specifying which names to exclude.

    Returns:
        Filtered pool with excluded Pokémon removed.
    """
    exclude_lower = {n.lower() for n in constraints.exclude}
    return [e for e in pool if e.pokemon_name.lower() not in exclude_lower]


def _validate_constraints(
    pool: list[PoolEntry],
    constraints: GenerationConstraints,
) -> None:
    """Assert that the given constraints are satisfiable against the pool.

    Args:
        pool: Full (unfiltered) pool.
        constraints: Constraints to validate.

    Raises:
        ValueError: If an include name has no competitive set, or if the pool
            has fewer than 6 distinct Pokémon after applying exclusions.
    """
    filtered = _apply_constraints(pool, constraints)
    filtered_names = {e.pokemon_name.lower() for e in filtered}
    for name in constraints.include:
        if name.lower() not in filtered_names:
            raise ValueError(
                f"include Pokémon '{name}' has no competitive set in the pool"
            )

    distinct = {e.pokemon_name for e in filtered}
    if len(distinct) < 6:
        raise ValueError(
            f"Pool has only {len(distinct)} distinct Pokémon after exclusions "
            f"(need at least 6)"
        )


def _sample_candidate(
    pool: list[PoolEntry],
    include: list[str],
    conn: Any,
    rng: random.Random,
) -> tuple[list[dict], list[PokemonBuild]]:
    """Build one 6-member candidate team using sampling heuristics.

    Applies three heuristics during slot-by-slot construction:
      1. No duplicate base species (blocks mega/gmax alongside their base form;
         regional forms are treated as distinct species and are allowed).
      2. No primary type appearing 3+ times in the partial team.
      3. Role diversity: no more than 2 physical or special sweepers.

    Rule 3 uses a retry budget before relaxing. Include names are locked in
    first, then remaining slots are filled from the filtered pool.

    Args:
        pool: Filtered pool (exclusions already applied).
        include: Pokémon names that must appear in the team.
        conn: Active psycopg2 connection (used to load builds for role checks).
        rng: Seeded Random instance.

    Returns:
        Tuple of (members_list, builds_list). members_list contains dicts with
        keys pokemon_name, set_id, set_name. May be shorter than 6 if the pool
        is exhausted mid-construction.
    """
    chosen_species: set[str] = set()   # tracks _base_species() of committed members
    type_counts: dict[str, int] = {}
    role_limits: dict[str, int] = {"physical_attacker": 0, "special_attacker": 0, "trick_room_setter": 0}
    members: list[dict] = []
    builds: list[PokemonBuild] = []

    def _commit(entry: PoolEntry, build: PokemonBuild) -> None:
        roles = detect_roles(build)
        members.append({
            "pokemon_name": entry.pokemon_name,
            "set_id": entry.set_id,
            "set_name": entry.set_name,
        })
        builds.append(build)
        chosen_species.add(_base_species(entry.pokemon_name))
        if entry.primary_type:
            type_counts[entry.primary_type] = type_counts.get(entry.primary_type, 0) + 1
        for role in roles:
            if role in role_limits:
                role_limits[role] += 1

    # Lock in required include Pokémon first (deduplicate to avoid Rule 1 violation)
    seen_include: set[str] = set()
    for name in include:
        name_lower = name.lower()
        if name_lower in seen_include:
            continue
        seen_include.add(name_lower)
        candidates = [e for e in pool if e.pokemon_name.lower() == name_lower]
        rng.shuffle(candidates)
        for entry in candidates:
            try:
                build = load_build(conn, entry.pokemon_name, entry.set_id)
                _commit(entry, build)
                break
            except ValueError:
                continue

    # Fill remaining slots
    remaining_slots = 6 - len(members)
    for _ in range(remaining_slots):
        # Rule 1 & 2: no duplicate base species, no primary type already at 3+
        eligible = [
            e for e in pool
            if _base_species(e.pokemon_name) not in chosen_species
            and type_counts.get(e.primary_type, 0) < 3
        ]
        if not eligible:
            # Relax Rule 2
            eligible = [
                e for e in pool
                if _base_species(e.pokemon_name) not in chosen_species
            ]
        if not eligible:
            break

        # Rule 3: avoid a third physical or special sweeper, with retry budget
        chosen_entry: PoolEntry | None = None
        chosen_build: PokemonBuild | None = None
        tried: set[int] = set()

        for _ in range(HEURISTIC_RETRY_BUDGET):
            candidates = [e for e in eligible if e.set_id not in tried]
            if not candidates:
                break
            entry = rng.choice(candidates)
            tried.add(entry.set_id)
            try:
                build = load_build(conn, entry.pokemon_name, entry.set_id)
            except ValueError:
                continue
            roles = detect_roles(build)
            violates = (
                ("physical_attacker" in roles and role_limits["physical_attacker"] >= MAX_PHYSICAL_ATTACKERS)
                or ("special_attacker" in roles and role_limits["special_attacker"] >= MAX_SPECIAL_ATTACKERS)
                or ("trick_room_setter" in roles and role_limits["trick_room_setter"] >= MAX_TR_SETTERS)
            )
            if not violates:
                chosen_entry = entry
                chosen_build = build
                break

        if chosen_entry is None:
            # Relax Rule 3: accept any eligible candidate
            candidates = list(eligible)
            rng.shuffle(candidates)
            for entry in candidates:
                try:
                    chosen_build = load_build(conn, entry.pokemon_name, entry.set_id)
                    chosen_entry = entry
                    break
                except ValueError:
                    continue

        if chosen_entry is not None:
            _commit(chosen_entry, chosen_build)

    return members, builds


def _is_acceptable(report: dict) -> bool:
    """Check whether a candidate team passes acceptance criteria.

    A team is accepted when it is valid (all TEAM_RULES met) and no type
    weakness count reaches WEAKNESS_THRESHOLD.

    Args:
        report: Analysis dict returned by analyze_team.

    Returns:
        True if the team meets all acceptance criteria.
    """
    if not report["valid"]:
        return False
    max_weakness = max(report["weaknesses"].values(), default=0)
    return max_weakness < WEAKNESS_THRESHOLD



def generate_teams(
    conn: Any,
    constraints: GenerationConstraints | None = None,
    rng: random.Random | None = None,
) -> dict:
    """Generate valid competitive teams using guided random sampling.

    Samples candidates from the competitive-set pool, validates each via the
    Sprint 6 analysis pipeline, and collects up to MAX_RESULTS accepted teams.
    Stops after MAX_ITERATIONS regardless of how many valid teams were found.

    Args:
        conn: Active psycopg2 connection.
        constraints: Optional include/exclude constraints. Defaults to no constraints.
        rng: Random instance (pass a seeded instance for deterministic tests).

    Returns:
        Dict with keys:
          - teams: list of accepted team dicts (score, members, analysis), sorted
            by score descending.
          - generated: total candidate iterations attempted.
          - valid_found: number of teams that passed acceptance criteria.

    Raises:
        ValueError: If an include name has no competitive set, or the pool has
            fewer than 6 distinct Pokémon after exclusions.
    """
    if rng is None:
        rng = random.Random()
    if constraints is None:
        constraints = GenerationConstraints()

    pool = _build_pool(conn)
    _validate_constraints(pool, constraints)
    filtered_pool = _apply_constraints(pool, constraints)

    results: list[dict] = []
    generated = 0

    while len(results) < MAX_RESULTS and generated < MAX_ITERATIONS:
        generated += 1
        members, builds = _sample_candidate(
            filtered_pool, constraints.include, conn, rng
        )
        if len(builds) < 6:
            continue
        report = analyze_team(builds)
        if _is_acceptable(report):
            lead = compute_lead_pair_score(builds)
            if lead["score"] == 0.0:
                continue
            scoring = score_team(report, builds)
            results.append({
                "score": scoring["score"],
                "breakdown": scoring["breakdown"],
                "members": members,
                "analysis": report,
            })

    results.sort(key=lambda t: t["score"], reverse=True)

    return {
        "teams": results,
        "generated": generated,
        "valid_found": len(results),
    }
