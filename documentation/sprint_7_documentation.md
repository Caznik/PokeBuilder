# Sprint 7 Documentation

## Overview

This document covers all components created during Sprint 7 of the PokeBuilder project — the Team Generation Engine. This sprint introduces the first end-user feature: instead of analysing a team the user provides, the system autonomously constructs competitive teams from the existing data layer and returns only those that pass validation.

---

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [Architecture](#architecture)
3. [Generation Strategy](#generation-strategy)
4. [Candidate Pool](#candidate-pool)
5. [Constraints](#constraints)
6. [Sampling Heuristics](#sampling-heuristics)
7. [Acceptance Criteria](#acceptance-criteria)
8. [Team Score](#team-score)
9. [REST API](#rest-api)
10. [Testing Strategy](#testing-strategy)
11. [Files Created / Modified](#files-created--modified)

---

## Feature Overview

Before this sprint the system could analyse a team the user explicitly specified. After this sprint it can generate valid competitive teams autonomously, optionally constrained by which Pokémon must or must not appear.

**Core capabilities added:**
- Build a candidate pool from all Pokémon with at least one ingested competitive set.
- Apply optional include/exclude constraints with pre-generation validation.
- Sample candidate teams using three lightweight heuristics to improve quality.
- Load and analyse each candidate through the Sprint 6 `load_team` + `analyze_team` pipeline.
- Accept or reject candidates based on role validation and weakness thresholds.
- Score and rank accepted teams.
- Expose `POST /team/generate` returning up to 5 valid teams with metadata.

---

## Architecture

```
POST /team/generate  {constraints?}
    ↓  generation.py (route)
    ↓  generate_teams(conn, constraints)
    ↓  _build_pool(conn)             → list[PoolEntry]
    ↓  _validate_constraints(pool)   → raises ValueError on bad input
    ↓  _apply_constraints(pool)      → filtered pool
    ↓  loop until valid_found == MAX_RESULTS or generated == MAX_ITERATIONS:
    │     _sample_candidate(pool, include, conn, rng)
    │       ├── lock in include Pokémon
    │       └── fill slots with heuristic-guided random picks
    │     analyze_team(builds)       → full report (Sprint 6)
    │     _is_acceptable(report)     → bool
    │     if acceptable → _score_team(report) + append
    ↓  sort by score descending
    ↓  GenerationResponse
```

`team_generator.py` owns the full loop. The route handles HTTP concerns only (body parsing, 400 errors, response model construction).

---

## Generation Strategy

**Approach C — Guided Random + Validation**

Team building is a constrained combinatorial search problem. Directly constructing a perfect team is brittle and hard to scale. Instead:

1. Build a pool of all Pokémon with competitive data.
2. Sample 6-member candidates using lightweight heuristics.
3. Load and analyse via Sprint 6 pipeline.
4. Accept or reject; repeat until `MAX_RESULTS` valid teams found or `MAX_ITERATIONS` reached.

This is the correct starting point. Evolutionary optimisation (Sprint 9) will build on this foundation.

## Constants

```python
MAX_RESULTS        = 5     # max teams returned
MAX_ITERATIONS     = 100   # candidate attempts before giving up
WEAKNESS_THRESHOLD = 3     # max Pokémon weak to the same type for acceptance
HEURISTIC_RETRY_BUDGET = 10  # retries per slot before relaxing Rule 3
```

---

## Candidate Pool

Pool construction query — includes primary type for sampling heuristics:

```sql
SELECT p.name, cs.id, cs.name, t.name AS primary_type
FROM competitive_sets cs
JOIN pokemon p ON cs.pokemon_id = p.id
LEFT JOIN pokemon_types pt ON p.id = pt.pokemon_id AND pt.slot = 1
LEFT JOIN types t ON pt.type_id = t.id
ORDER BY p.name, cs.id
```

Each row becomes a `PoolEntry(pokemon_name, set_id, set_name, primary_type)` named tuple. Only Pokémon with at least one competitive set appear. Pool members are weighted equally.

---

## Constraints

```python
class GenerationConstraints(BaseModel):
    include: list[str] = []   # Pokémon names that must appear
    exclude: list[str] = []   # Pokémon names that must not appear
```

**Pre-generation validation** (raises `ValueError` → HTTP 400):
- Any name in `include` must have ≥ 1 competitive set in the pool.
- Pool after exclusions must have ≥ 6 distinct Pokémon.

Include Pokémon are locked into the team first (a random set is chosen for each). Remaining slots are filled from the filtered pool.

`style` is deferred to Sprint 9 (evolutionary optimiser).

---

## Sampling Heuristics

Applied slot-by-slot during candidate construction:

**Rule 1 — No duplicate Pokémon**  
Each team member must be a different Pokémon (tracked by name).

**Rule 2 — No type-cluster redundancy**  
A candidate is skipped if its primary type already appears 3+ times in the partial team. If this filter empties the eligible set, Rule 2 is relaxed.

**Rule 3 — Role diversity pressure**  
If the partial team already has 2 `physical_sweeper`s, candidates that would be a third are skipped. Same for `special_sweeper`s. A retry budget of `HEURISTIC_RETRY_BUDGET` attempts is used per slot; if no valid candidate is found, Rule 3 is relaxed.

Rules are best-effort — relaxation prevents the sampling from hanging on constrained pools.

---

## Acceptance Criteria

A candidate is accepted when:

1. `analysis["valid"] == True` — all Sprint 6 `TEAM_RULES` are satisfied.
2. No type in `analysis["weaknesses"]` has count ≥ `WEAKNESS_THRESHOLD`.

Condition 2 is enforced by the generator (not the validator), keeping `TEAM_RULES` focused on role composition.

---

## Team Score

A quality metric that differentiates accepted teams:

```
score = 1.0 - (max_weakness_count * 0.05)
```

Where `max_weakness_count` is the highest count across all weakness types. All accepted teams satisfy all `TEAM_RULES`, so the role-satisfaction component is always 1.0. Accepted teams are returned sorted by `final_score` descending.

---

## REST API

**File:** `src/api/routes/generation.py`

### `POST /team/generate`

**Request** (body optional):
```json
{
  "constraints": {
    "include": ["garchomp"],
    "exclude": ["mewtwo"]
  }
}
```
An empty `{}` or omitted body generates with no constraints.

**Response 200:**
```json
{
  "teams": [
    {
      "score": 0.95,
      "members": [
        {"pokemon_name": "garchomp",   "set_id": 1, "set_name": "Choice Scarf"},
        {"pokemon_name": "ferrothorn", "set_id": 7, "set_name": "Defensive"}
      ],
      "analysis": {
        "valid": true,
        "issues": [],
        "roles": {"physical_sweeper": 2, "special_sweeper": 1, "tank": 1, "hazard_setter": 1, "pivot": 1, "hazard_removal": 0, "support": 0},
        "weaknesses": {"ice": 1},
        "resistances": {"steel": 3},
        "coverage": {
          "covered_types": ["grass", "steel"],
          "missing_types": ["fairy"]
        }
      }
    }
  ],
  "generated": 47,
  "valid_found": 5
}
```

**Response 200 (no valid teams found):** `teams: []`, `valid_found: 0` — not an error; caller may retry or relax constraints.

**Response 400:** Invalid constraints — include Pokémon has no competitive set, or pool too small after exclusions.

### Pydantic Models (`src/api/models/generation.py`)

| Model | Fields |
|---|---|
| `GenerationConstraints` | `include` (list[str], default []), `exclude` (list[str], default []) |
| `GenerateRequest` | `constraints` (GenerationConstraints \| None) |
| `GenerationMember` | `pokemon_name`, `set_id`, `set_name` (str \| None) |
| `TeamAnalysis` | `valid`, `issues`, `roles`, `weaknesses`, `resistances`, `coverage` |
| `TeamResult` | `score`, `members`, `analysis` |
| `GenerationResponse` | `teams`, `generated`, `valid_found` |

---

## Testing Strategy

| File | Tests | Approach |
|---|---|---|
| `tests/test_team_generator.py` | 42 | Mock DB cursor, `load_build`, `detect_roles`, `analyze_team`; assert pool construction, constraint validation, heuristics, scoring, and loop behaviour |
| `tests/test_generation_api.py` | 14 | FastAPI `TestClient`; mock `generate_teams` and `get_db_connection`; assert response shape and error codes |

**Total: 56 tests**

Random sampling is made deterministic in tests by passing a seeded `random.Random` instance to `generate_teams` and `_sample_candidate`.

```bash
pytest tests/test_team_generator.py tests/test_generation_api.py -v
```

---

## Files Created / Modified

### New Files

| File | Purpose |
|---|---|
| `src/api/models/generation.py` | GenerationConstraints, GenerateRequest, GenerationMember, TeamAnalysis, TeamResult, GenerationResponse |
| `src/api/services/team_generator.py` | Pool building, constraint validation, heuristic sampling, generation loop, scoring |
| `src/api/routes/generation.py` | POST /team/generate route |
| `tests/test_team_generator.py` | Generator service unit tests (42 tests) |
| `tests/test_generation_api.py` | API integration tests (14 tests) |
| `documentation/sprint_7_documentation.md` | This document |

### Modified Files

| File | Change |
|---|---|
| `src/api/main.py` | Registered `generation_router` |
| `src/api/routes/__init__.py` | Exported `generation_router` |

---

## Summary

Sprint 7 successfully delivered:

1. **Candidate pool** — all Pokémon with competitive sets, extended with primary type for heuristics
2. **Constraint system** — include/exclude with pre-generation validation and 400 errors
3. **Sampling heuristics** — three rules (no duplicates, type clustering cap, role diversity) applied slot-by-slot with relaxation fallbacks
4. **Generation loop** — guided random sampling with Sprint 6 analysis pipeline, up to 100 iterations
5. **Scoring** — weakness-penalty score for ranking accepted teams
6. **REST endpoint** — `POST /team/generate` with full response including metadata
7. **56 tests** — all passing, deterministic via seeded RNG

The system now supports:
- ✅ Pokémon data (Sprint 1)
- ✅ Abilities and relationships (Sprint 1)
- ✅ Types and effectiveness (Sprints 1–3)
- ✅ Moves and learnsets (Sprint 2)
- ✅ Stat calculation with IVs, EVs, Natures (Sprint 4)
- ✅ Competitive sets from Smogon (Sprint 5)
- ✅ Team role analysis, validation, weakness/coverage report (Sprint 6)
- ✅ Autonomous team generation with constraints and scoring (Sprint 7)

---

*Last updated: April 28, 2026*
