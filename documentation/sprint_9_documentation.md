# Sprint 9 Documentation

## Overview

This document covers all components created during Sprint 9 of the PokeBuilder project — the Genetic Algorithm (GA) Team Optimizer. This sprint takes the existing scorer and generator and adds an evolutionary layer on top: a population of valid teams is seeded, then evolved across multiple generations using tournament selection, one-point crossover, and two-type mutation to converge on high-scoring competitive compositions.

---

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [Architecture](#architecture)
3. [GA Parameters](#ga-parameters)
4. [GA Operators](#ga-operators)
5. [Evolution Loop](#evolution-loop)
6. [Fitness Evaluation & Caching](#fitness-evaluation--caching)
7. [Sprint 7 & 8 Integration](#sprint-7--8-integration)
8. [REST API](#rest-api)
9. [Testing Strategy](#testing-strategy)
10. [Files Created / Modified](#files-created--modified)

---

## Feature Overview

Before this sprint the generator built teams by random sampling and filtering — good, but unable to improve on what it found. The optimizer adds directed search: starting from a seeded population of valid teams, it applies selection pressure and genetic operators to steer the population toward higher `score_team` values.

**Core capabilities added:**
- A full GA evolution loop: seeded initial population → tournament selection → crossover → mutation → steady-state replacement.
- Two mutation types: **Replace Member** (swap one Pokémon for a new species) and **Swap Set** (keep the Pokémon, change its competitive set).
- A **repair operator** that enforces the one-species-per-team constraint after any genetic operation that could violate it.
- A **fitness cache** (keyed by order-independent `frozenset`) to avoid re-scoring identical teams.
- `POST /team/optimize` — expose the full optimizer via REST with optional constraints and tunable GA parameters.

---

## Architecture

```
POST /team/optimize  {constraints?, population_size?, generations?}
    ↓  optimize_team(conn, constraints, population_size, generations)   (Sprint 9)
    │
    │  Seed phase
    │     _build_pool / _validate_constraints / _apply_constraints      (Sprint 7)
    │     _seed_population → _sample_candidate + _is_acceptable         (Sprint 7)
    │
    │  Evolution loop (× generations)
    │     _evaluate(chromosome, conn, cache, eval_count)
    │     │   load_build × 6                                            (Sprint 6)
    │     │   analyze_team                                              (Sprint 6)
    │     │   score_team → fitness [0.0, 10.0]                          (Sprint 8)
    │     _tournament_select → parent A, parent B
    │     _crossover(parent_a, parent_b) → naive child
    │     _repair(child, pool)           → constraint-safe child
    │     _mutate(child, pool)           → (optionally) altered + repaired child
    │     steady-state replacement: keep top population_size
    │
    ↓  best_teams[:MAX_RESULTS]  (score, breakdown, members, analysis per team)
    ↓  OptimizationResponse {best_teams, generations_run, initial_population, evaluations}
```

`team_optimizer.py` owns all GA logic and imports operators from `team_generator.py` — no duplication of pool-building or constraint handling.

---

## GA Parameters

| Constant | Default | Cap | Meaning |
|---|---|---|---|
| `POPULATION_SIZE` | 50 | 100 | Number of chromosomes in the population |
| `GENERATIONS` | 30 | 50 | Number of evolution iterations |
| `TOURNAMENT_K` | 3 | — | Contestants per tournament selection |
| `CROSSOVER_RATE` | 0.80 | — | Probability of crossover vs. cloning parent A |
| `MUTATION_RATE` | 0.15 | — | Probability of applying mutation to a child |
| `CHILDREN_PER_GENERATION_RATIO` | 5 | — | `population_size // 5` children produced per generation |
| `MAX_REPAIR_TRIES` | 20 | — | Repair attempts per duplicate slot before giving up |
| `MAX_SEED_ATTEMPTS_MULTIPLIER` | 10 | — | Max seed attempts = `population_size × 10` |
| `MUTATION_TYPE_SPLIT` | 0.5 | — | P(type-1 Replace Member) vs P(type-2 Swap Set) |

`population_size` and `generations` are capped in both the service and the Pydantic model — invalid values are rejected (< 1) while oversized values are silently clamped (> cap).

---

## GA Operators

### `_seed_population(pool, conn, rng, size) → list[Chromosome]`

Builds the initial population by repeatedly calling the Sprint 7 `_sample_candidate` + `_is_acceptable` pipeline. Each accepted sample becomes a `Chromosome` (list of `(pokemon_name, set_id)` pairs). Stops when `size` chromosomes are found or `size × MAX_SEED_ATTEMPTS_MULTIPLIER` attempts are exhausted — the population may be smaller than `size` on constrained or sparse pools.

---

### `_tournament_select(population, scores, k, rng) → Chromosome`

Draws `min(k, len(population))` random contestants and returns the one with the highest cached fitness score. Deterministic given the same RNG state — the winning chromosome is always the best of the sample, not a probabilistic draw.

---

### `_crossover(parent_a, parent_b, rng) → Chromosome`

One-point crossover: picks a cut point uniformly from `[1, TEAM_SIZE - 1]` (= 1–5 inclusive), then produces `parent_a[:cut] + parent_b[cut:]`. This guarantees:
- `child[0]` always comes from `parent_a` (cut ≥ 1).
- `child[5]` always comes from `parent_b` (cut ≤ 5).

The naive child may contain duplicate base species and is always passed through `_repair` before use.

---

### `_repair(child, pool, rng) → Chromosome`

Scans slots left to right. The first occurrence of any base species is kept; subsequent duplicates trigger up to `MAX_REPAIR_TRIES` random draws from the pool to find a non-duplicate replacement. If the budget is exhausted (e.g. tiny constrained pool) the duplicate survives — repair is best-effort, not guaranteed. The original list is never mutated; a copy is returned.

`_base_species` (imported from `team_generator`) strips form suffixes (e.g. `"rotom-wash"` → `"rotom"`) so different forms of the same Pokémon count as the same species.

---

### `_mutate(child, pool, rng) → Chromosome`

Applies one of two mutation types, then calls `_repair`:

**Type 1 — Replace Member** (probability 0.5):  
Picks a random slot. Builds a filtered pool excluding all base species already on the team (excluding the slot being replaced). Draws a replacement from the filtered pool, falling back to the full pool if the filtered pool is empty.

**Type 2 — Swap Set** (probability 0.5):  
Picks a random slot. Keeps the Pokémon name; replaces the set ID with an alternative set for that Pokémon from the pool. No-op if only one set exists for that species.

---

## Evolution Loop

```python
for _ in range(generations):
    if not population:
        break

    # Score every individual (cache hits are free)
    scores = {_cache_key(ind): _evaluate(ind, conn, cache, eval_count)
              for ind in population}

    # Produce children_per_gen new children
    children = []
    while len(children) < children_per_gen:
        p1 = _tournament_select(population, scores, TOURNAMENT_K, rng)
        p2 = _tournament_select(population, scores, TOURNAMENT_K, rng)
        child = _crossover(p1, p2, rng) if rng.random() < CROSSOVER_RATE else list(p1)
        child = _mutate(child, pool, rng) if rng.random() < MUTATION_RATE else _repair(child, pool, rng)
        children.append(child)

    # Steady-state replacement: keep top population_size
    population = sorted(population + children,
                        key=lambda ind: _evaluate(ind, conn, cache, eval_count),
                        reverse=True)[:population_size]
```

Each generation introduces `population_size // 5` new children (minimum 1). The combined pool of old individuals and children is sorted by fitness and truncated to `population_size`. This keeps the elite alive — the best team found so far can never be evicted by a worse child.

---

## Fitness Evaluation & Caching

### `_evaluate(chromosome, conn, cache, eval_count) → float`

The fitness of a chromosome is its `score_team` score on the `[0.0, 10.0]` scale.

**Cache:** keyed by `frozenset(chromosome)` — order-independent, so the same 6-member team in any slot arrangement hits the same entry. `eval_count` (a single-element list) counts only cache misses, i.e. actual `score_team` calls. This count is returned in the response as `evaluations`.

Without caching, a population of 50 evolved for 30 generations would require up to `50 × 30 = 1500+` evaluations; the cache typically reduces this by 30–50% on large pools where many children duplicate existing individuals.

---

## Sprint 7 & 8 Integration

`team_optimizer.py` is a consumer of both previous sprints — it adds no new scoring or generation logic:

| Sprint | What the optimizer reuses |
|---|---|
| Sprint 7 | `_build_pool`, `_validate_constraints`, `_apply_constraints`, `_sample_candidate`, `_is_acceptable`, `PoolEntry`, `MAX_RESULTS`, `_base_species` |
| Sprint 8 | `score_team` (fitness function), `ScoreBreakdown` / `ScoreComponent` (response models) |
| Sprint 6 | `load_build`, `analyze_team` (called inside `_evaluate` and in the final result assembly) |

The optimizer response shape for each team (`score`, `breakdown`, `members`, `analysis`) is identical to `POST /team/generate` — callers can treat results from either endpoint the same way.

---

## REST API

### `POST /team/optimize`

**File:** `src/api/routes/optimization.py`

**Request body** (all fields optional — defaults apply):
```json
{
  "population_size": 50,
  "generations": 30,
  "constraints": {
    "include": ["garchomp", "ferrothorn"],
    "exclude": ["wobbuffet"]
  }
}
```

| Field | Type | Default | Validation |
|---|---|---|---|
| `population_size` | int | 50 | ≥ 1; clamped to 100 |
| `generations` | int | 30 | ≥ 1; clamped to 50 |
| `constraints` | object | null | Same schema as `POST /team/generate` |

**Response 200:**
```json
{
  "best_teams": [
    {
      "score": 9.14,
      "breakdown": {
        "coverage":  {"score": 0.94, "reason": "missing fairy"},
        "defensive": {"score": 1.00, "reason": "no shared weaknesses"},
        "role":      {"score": 1.00, "reason": "all role minimums met"},
        "speed":     {"score": 1.00, "reason": "3 fast Pokémon, 1 priority user(s)"}
      },
      "members": [
        {"pokemon_name": "garchomp",   "set_id": 1, "set_name": null},
        {"pokemon_name": "ferrothorn", "set_id": 2, "set_name": null},
        {"pokemon_name": "rotom-wash", "set_id": 3, "set_name": null},
        {"pokemon_name": "clefable",   "set_id": 4, "set_name": null},
        {"pokemon_name": "heatran",    "set_id": 5, "set_name": null},
        {"pokemon_name": "landorus",   "set_id": 6, "set_name": null}
      ],
      "analysis": { ... }
    }
  ],
  "generations_run": 30,
  "initial_population": 47,
  "evaluations": 287
}
```

| Response field | Meaning |
|---|---|
| `best_teams` | Up to `MAX_RESULTS` teams, sorted by score descending |
| `generations_run` | The (capped) number of GA generations executed |
| `initial_population` | Actual seed population size (may be < `population_size` on sparse pools) |
| `evaluations` | Number of `score_team` calls (cache misses only) |

**Response 400** — `ValueError` from constraint validation (unknown Pokémon, pool too small).  
**Response 422** — `population_size < 1` or `generations < 1`.

### Pydantic Models (`src/api/models/optimization.py`)

| Model | Fields |
|---|---|
| `OptimizeRequest` | `constraints` (GenerationConstraints \| None), `population_size` (int, default 50), `generations` (int, default 30) |
| `OptimizationResponse` | `best_teams` (list[TeamResult]), `generations_run` (int), `initial_population` (int), `evaluations` (int) |

Validators on `OptimizeRequest` mirror the service-level caps — oversized values are silently clamped to 100 / 50 by `field_validator` before reaching the service.

---

## Testing Strategy

| File | Tests | Approach |
|---|---|---|
| `tests/test_team_optimizer.py` | 40 | Pure-function unit tests for all 7 GA primitives (`_cache_key`, `_seed_population`, `_evaluate`, `_tournament_select`, `_crossover`, `_repair`, `_mutate`) plus 8 `optimize_team` integration tests; mocks DB and Sprint 6/7/8 dependencies; covers edge cases: cache hits, exhausted repair budget, empty filtered pool fallback, population-size and generation caps |
| `tests/test_optimization_api.py` | 14 | FastAPI `TestClient`; mocks `get_db_connection` and `optimize_team`; asserts response shape, field types, HTTP 400 on `ValueError`, HTTP 422 on invalid params, and silent clamping of oversized params |

**Total new tests: 54**

```bash
pytest tests/test_team_optimizer.py tests/test_optimization_api.py -v
```

---

## Files Created / Modified

### New Files

| File | Purpose |
|---|---|
| `src/api/services/team_optimizer.py` | Full GA engine: `_seed_population`, `_evaluate`, `_tournament_select`, `_crossover`, `_repair`, `_mutate`, `optimize_team` |
| `src/api/models/optimization.py` | `OptimizeRequest`, `OptimizationResponse` Pydantic models |
| `src/api/routes/optimization.py` | `POST /team/optimize` route |
| `tests/test_team_optimizer.py` | 40 GA service unit tests |
| `tests/test_optimization_api.py` | 14 optimization API integration tests |
| `documentation/sprint_9_documentation.md` | This document |

### Modified Files

| File | Change |
|---|---|
| `src/api/routes/__init__.py` | Exported `optimization_router` |
| `src/api/main.py` | Registered `optimization_router` |

---

## Summary

Sprint 9 successfully delivered:

1. **Full GA engine** — tournament selection, one-point crossover, two-type mutation (replace member / swap set), and a repair operator that enforces base-species uniqueness after every genetic operation
2. **Fitness caching** — order-independent `frozenset` key avoids re-scoring identical teams; `evaluations` counter exposes actual compute cost to callers
3. **Steady-state replacement** — elitism preserved; top individuals survive every generation
4. **`POST /team/optimize`** — fully tunable via `population_size`, `generations`, and the existing constraint system; oversized params clamped, invalid params rejected
5. **54 new tests** — covering all 7 GA primitives and the full optimizer lifecycle

The system now supports:
- ✅ Pokémon data (Sprint 1)
- ✅ Abilities and relationships (Sprint 1)
- ✅ Types and effectiveness (Sprints 1–3)
- ✅ Moves and learnsets (Sprint 2)
- ✅ Stat calculation with IVs, EVs, Natures (Sprint 4)
- ✅ Competitive sets from Smogon (Sprint 5)
- ✅ Team role analysis, validation, weakness/coverage report (Sprint 6)
- ✅ Autonomous team generation with constraints and scoring (Sprint 7)
- ✅ Multi-component team scoring engine with explainable breakdown (Sprint 8)
- ✅ Genetic Algorithm team optimizer with directed evolutionary search (Sprint 9)

---

*Last updated: April 29, 2026*
