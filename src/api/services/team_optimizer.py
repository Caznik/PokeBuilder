# src/api/services/team_optimizer.py
"""Genetic Algorithm engine for evolving competitive Pokémon teams."""

import random
from typing import Any

from ..models.generation import GenerationConstraints
from .team_generator import (
    _apply_constraints,
    _base_species,
    _build_pool,
    _is_acceptable,
    _sample_candidate,
    _validate_constraints,
    MAX_RESULTS,
    PoolEntry,
)
from .team_loader import load_build
from .team_analysis import analyze_team
from .team_scorer import score_team

# Type alias
Chromosome = list[tuple[str, int]]

# Constants
POPULATION_SIZE = 50
GENERATIONS = 30
TOURNAMENT_K = 3
CROSSOVER_RATE = 0.80
MUTATION_RATE = 0.15
CHILDREN_PER_GENERATION_RATIO = 5  # one fifth of population replaced per generation
MAX_REPAIR_TRIES = 20
MAX_RESULTS_OPTIMIZER = MAX_RESULTS
MAX_SEED_ATTEMPTS_MULTIPLIER = 10
TEAM_SIZE = 6
MUTATION_TYPE_SPLIT = 0.5

MAX_POPULATION_SIZE = 100
MAX_GENERATIONS = 50


def _cache_key(chromosome: Chromosome) -> frozenset:
    """Return an order-independent cache key for a chromosome.

    Args:
        chromosome: List of (pokemon_name, set_id) pairs.

    Returns:
        frozenset of (pokemon_name, set_id) pairs.
    """
    return frozenset(chromosome)


def _seed_population(
    pool: list[PoolEntry],
    conn: Any,
    rng: random.Random,
    size: int,
) -> list[Chromosome]:
    """Seed the initial GA population with structurally valid teams.

    Uses a relaxed acceptance criterion (only requires team validity, not the
    weakness threshold) so the GA starts from a larger, more diverse gene pool.
    Duplicate chromosomes are excluded.

    Args:
        pool: Filtered pool of PoolEntry tuples.
        conn: Active psycopg2 connection.
        rng: Seeded Random instance.
        size: Target population size.

    Returns:
        List of unique Chromosomes (up to size). May be smaller if valid teams are scarce.
    """
    population: list[Chromosome] = []
    seen: set[frozenset] = set()
    max_attempts = size * MAX_SEED_ATTEMPTS_MULTIPLIER
    attempts = 0
    while len(population) < size and attempts < max_attempts:
        attempts += 1
        members, builds = _sample_candidate(pool, [], conn, rng)
        if len(builds) < 6:
            continue
        report = analyze_team(builds)
        if not report["valid"]:
            continue
        chromosome = [(m["pokemon_name"], m["set_id"]) for m in members]
        key = _cache_key(chromosome)
        if key not in seen:
            seen.add(key)
            population.append(chromosome)
    return population


def _evaluate(
    chromosome: Chromosome,
    conn: Any,
    cache: dict[frozenset, float],
    eval_count: list[int],
) -> float:
    """Compute the fitness score for a chromosome, using cache when available.

    Args:
        chromosome: List of (pokemon_name, set_id) pairs.
        conn: Active psycopg2 connection.
        cache: Shared fitness cache (mutated in place).
        eval_count: Single-element list tracking actual score_team calls.

    Returns:
        Fitness score in [0.0, 10.0].
    """
    key = _cache_key(chromosome)
    if key in cache:
        return cache[key]
    builds = [load_build(conn, name, sid) for name, sid in chromosome]
    report = analyze_team(builds)
    scoring = score_team(report, builds)
    score = float(scoring["score"])
    cache[key] = score
    eval_count[0] += 1
    return score


def _tournament_select(
    population: list[Chromosome],
    scores: dict[frozenset, float],
    k: int,
    rng: random.Random,
) -> Chromosome:
    """Select the best individual from a random tournament sample.

    Args:
        population: Current population of chromosomes.
        scores: Mapping from cache_key -> fitness score.
        k: Tournament size.
        rng: Seeded Random instance.

    Returns:
        The highest-scoring individual among the k sampled contestants.
    """
    sample_size = min(k, len(population))
    contestants = rng.sample(population, sample_size)
    return max(contestants, key=lambda ind: scores[_cache_key(ind)])


def _crossover(
    parent_a: Chromosome,
    parent_b: Chromosome,
    rng: random.Random,
) -> Chromosome:
    """One-point crossover between two parent chromosomes.

    Args:
        parent_a: First parent chromosome (6 members).
        parent_b: Second parent chromosome (6 members).
        rng: Seeded Random instance.

    Returns:
        Naive child chromosome: parent_a[:cut] + parent_b[cut:],
        where cut is chosen uniformly from 1–5 inclusive.
    """
    cut = rng.randint(1, TEAM_SIZE - 1)
    return list(parent_a[:cut]) + list(parent_b[cut:])


def _repair(
    child: Chromosome,
    pool: list[PoolEntry],
    rng: random.Random,
) -> Chromosome:
    """Repair duplicate base-species violations in a chromosome.

    Scans slots left to right. For each slot whose base species already
    appears earlier, attempts up to MAX_REPAIR_TRIES random pool draws
    to find a non-duplicate replacement. Keeps the duplicate if the
    budget is exhausted (rare on large pools).

    Args:
        child: Chromosome to repair (not mutated — a copy is made).
        pool: Pool of valid PoolEntry choices.
        rng: Seeded Random instance.

    Returns:
        Repaired chromosome with at most one entry per base species.
    """
    child = list(child)
    seen: set[str] = set()
    for i, (name, _sid) in enumerate(child):
        base = _base_species(name)
        if base not in seen:
            seen.add(base)
        else:
            replaced = False
            for _ in range(MAX_REPAIR_TRIES):
                entry = rng.choice(pool)
                rep_base = _base_species(entry.pokemon_name)
                if rep_base not in seen:
                    child[i] = (entry.pokemon_name, entry.set_id)
                    seen.add(rep_base)
                    replaced = True
                    break
            if not replaced:
                seen.add(base)
    return child


def _mutate(
    child: Chromosome,
    pool: list[PoolEntry],
    rng: random.Random,
) -> Chromosome:
    """Apply one of two mutation types to a chromosome, then repair.

    Type 1 — Replace Member: swap one slot with a pool entry whose base
    species is not already on the team. Falls back to any pool entry if
    the filtered pool is empty.

    Type 2 — Swap Set: keep the Pokémon, replace its competitive set
    with an alternative set from the pool. No-op if only one set exists.

    Repair is called after mutation to maintain base-species uniqueness.

    Args:
        child: Chromosome to mutate (a copy is made internally).
        pool: Filtered pool of PoolEntry choices.
        rng: Seeded Random instance.

    Returns:
        Mutated and repaired chromosome.
    """
    child = list(child)
    if rng.random() < MUTATION_TYPE_SPLIT:
        # Type 1: Replace Member
        slot = rng.randrange(TEAM_SIZE)
        current_bases = {
            _base_species(n) for n, _ in child if n != child[slot][0]
        }
        filtered = [e for e in pool if _base_species(e.pokemon_name) not in current_bases]
        if not filtered:
            filtered = pool
        entry = rng.choice(filtered)
        child[slot] = (entry.pokemon_name, entry.set_id)
    else:
        # Type 2: Swap Set
        slot = rng.randrange(TEAM_SIZE)
        name = child[slot][0]
        alts = [e for e in pool if e.pokemon_name == name and e.set_id != child[slot][1]]
        if alts:
            child[slot] = (name, rng.choice(alts).set_id)
    return _repair(child, pool, rng)


def optimize_team(
    conn: Any,
    constraints: GenerationConstraints | None = None,
    population_size: int = POPULATION_SIZE,
    generations: int = GENERATIONS,
    rng: random.Random | None = None,
) -> dict:
    """Run the GA evolution loop to find high-scoring competitive teams.

    Seeds an initial population using the Sprint 7 generator, then evolves it
    for the specified number of generations using tournament selection, one-point
    crossover, mutation, and steady-state replacement.

    Args:
        conn: Active psycopg2 connection.
        constraints: Optional include/exclude constraints (no constraints if None).
        population_size: Target population size (capped at 100).
        generations: Number of evolution generations to run (capped at 50).
        rng: Seeded Random instance (fresh Random() if None).

    Returns:
        Dict with keys:
          - best_teams: list of up to MAX_RESULTS team dicts
            (score, breakdown, members, analysis).
          - generations_run: the capped generations parameter (≤ MAX_GENERATIONS).
          - initial_population: size of the seeded population before evolution.
          - evaluations: number of actual score_team calls (cache misses only).

    Raises:
        ValueError: If constraints reference Pokémon not in the pool, or the
            pool has fewer than 6 distinct Pokémon after exclusions.
    """
    if rng is None:
        rng = random.Random()
    if constraints is None:
        constraints = GenerationConstraints()

    population_size = min(population_size, MAX_POPULATION_SIZE)
    generations = min(generations, MAX_GENERATIONS)

    pool = _build_pool(conn)
    _validate_constraints(pool, constraints)
    filtered_pool = _apply_constraints(pool, constraints)

    population = _seed_population(filtered_pool, conn, rng, population_size)
    initial_pop_size = len(population)
    cache: dict[frozenset, float] = {}
    eval_count = [0]

    children_per_gen = max(1, population_size // CHILDREN_PER_GENERATION_RATIO)

    # Hall of fame: best unique chromosomes seen across all generations,
    # keyed by frozenset → (score, chromosome). Tracks diverse top teams
    # even when the final population has converged.
    hof: dict[frozenset, tuple[float, Chromosome]] = {}

    def _update_hof(chrom: Chromosome) -> None:
        key = _cache_key(chrom)
        score = _evaluate(chrom, conn, cache, eval_count)
        if key not in hof or score > hof[key][0]:
            hof[key] = (score, list(chrom))

    for chrom in population:
        _update_hof(chrom)

    for _ in range(generations):
        if not population:
            break
        scores = {
            _cache_key(ind): _evaluate(ind, conn, cache, eval_count)
            for ind in population
        }

        children: list[Chromosome] = []
        while len(children) < children_per_gen:
            p1 = _tournament_select(population, scores, TOURNAMENT_K, rng)
            p2 = _tournament_select(population, scores, TOURNAMENT_K, rng)
            if rng.random() < CROSSOVER_RATE:
                child = _crossover(p1, p2, rng)
            else:
                child = list(p1)
            if rng.random() < MUTATION_RATE:
                child = _mutate(child, filtered_pool, rng)
            else:
                child = _repair(child, filtered_pool, rng)
            children.append(child)
            _update_hof(child)

        population = sorted(
            population + children,
            key=lambda ind: _evaluate(ind, conn, cache, eval_count),
            reverse=True,
        )[:population_size]

        for chrom in population:
            _update_hof(chrom)

    # Pick top unique teams from the hall of fame, sorted by score descending
    best = [
        chrom for _, chrom in sorted(hof.values(), key=lambda x: x[0], reverse=True)
    ][:MAX_RESULTS_OPTIMIZER]

    pool_by_set = {(e.pokemon_name, e.set_id): e for e in filtered_pool}
    best_teams = []
    for chrom in best:
        builds = [load_build(conn, name, sid) for name, sid in chrom]
        report = analyze_team(builds)
        scoring = score_team(report, builds)
        members = []
        for (n, s), build in zip(chrom, builds):
            entry = pool_by_set.get((n, s))
            members.append({
                "pokemon_name": n,
                "set_id": s,
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

    return {
        "best_teams": best_teams,
        "generations_run": generations,
        "initial_population": initial_pop_size,
        "evaluations": eval_count[0],
    }
