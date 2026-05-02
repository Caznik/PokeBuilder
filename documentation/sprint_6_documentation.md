# Sprint 6 Documentation

## Overview

This document covers all components created during Sprint 6 of the PokeBuilder project — the Team Analysis Engine. This sprint introduces the first strategic layer: given a team of 6 Pokémon builds, the system evaluates role composition, validates it against configurable rules, and reports shared type weaknesses/resistances and offensive move coverage.

---

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [Architecture](#architecture)
3. [Domain Model](#domain-model)
4. [Role Detection](#role-detection)
5. [Team Validation](#team-validation)
6. [Weakness & Resistance Analysis](#weakness--resistance-analysis)
7. [Coverage Analysis](#coverage-analysis)
8. [REST API](#rest-api)
9. [Testing Strategy](#testing-strategy)
10. [Files Created / Modified](#files-created--modified)

---

## Feature Overview

Before this sprint the system could retrieve Pokémon data, calculate stats, and look up competitive sets. After this sprint it can accept a full team of 6 Pokémon builds and return a unified strategic analysis.

**Core capabilities added:**
- Load a full `PokemonBuild` from the DB for each team member (competitive set + computed stats + move details).
- Detect roles for each Pokémon (multiple roles allowed, not mutually exclusive).
- Validate the team against a configurable minimum-role rule set.
- Aggregate type weaknesses and resistances across the team.
- Compute offensive coverage: which of the 18 types the team can hit super-effectively.
- Expose `POST /team/analyze` returning all of the above in a single response.

---

## Architecture

```
POST /team/analyze  [{pokemon_name, set_id}, ...]
    ↓  team_loader.py
    ↓  load each PokemonBuild from DB (set + computed stats + move details)
    ↓  team_analysis.py
    ├── role_service.py      detect_roles(build)      → list[str]
    ├── team_validator.py    validate_team(builds)     → {valid, issues, roles}
    ├── weakness_service.py  analyze_weaknesses(builds)→ {weaknesses, resistances}
    └── coverage_service.py  analyze_coverage(builds)  → {covered_types, missing_types}
    ↓  TeamAnalysisResponse (Pydantic)
```

`team_analysis.py` is a thin combiner — it delegates to each sub-service and merges results into a single dict passed to the route.

---

## Domain Model

### `PokemonBuild` (internal dataclass)

| Field | Type | Source |
|---|---|---|
| `pokemon_name` | str | input |
| `set_id` | int | input |
| `types` | list[str] | `pokemon_types` JOIN `types` |
| `nature` | str \| None | `natures` via `competitive_sets` |
| `ability` | str \| None | `abilities` via `competitive_sets` |
| `item` | str \| None | `competitive_sets.item` |
| `stats` | dict[str, int] | computed via Sprint 4 `stat_service` |
| `moves` | list[MoveDetail] | `competitive_set_moves` JOIN `moves` JOIN `types` JOIN `move_categories` |

### `MoveDetail` (internal dataclass)

| Field | Type |
|---|---|
| `name` | str |
| `type` | str |
| `category` | str — `"physical"` / `"special"` / `"status"` |

Both are defined in `src/api/models/team.py` and used internally across all services. They are not exposed directly in the API response.

---

## Role Detection

**File:** `src/api/services/role_service.py`

### Constants

```python
SPEED_THRESHOLD     = 280
ATTACK_THRESHOLD    = 300
SP_ATTACK_THRESHOLD = 300
DEFENSE_THRESHOLD   = 200
HP_THRESHOLD        = 300

HAZARD_SETTER_MOVES  = {"stealth-rock", "spikes", "toxic-spikes", "sticky-web"}
HAZARD_REMOVAL_MOVES = {"defog", "rapid-spin", "mortal-spin"}
PIVOT_MOVES          = {"u-turn", "volt-switch", "flip-turn", "teleport"}
SUPPORT_MOVES        = {"toxic", "thunder-wave", "will-o-wisp", "wish",
                        "heal-bell", "aromatherapy", "encore", "taunt"}
```

### `detect_roles(build: PokemonBuild) -> list[str]`

Returns a list of role strings for a single Pokémon. A Pokémon can hold multiple roles simultaneously.

| Role | Stat condition | Move condition |
|---|---|---|
| `physical_sweeper` | attack ≥ 300 AND speed ≥ 280 | majority of damaging moves are physical |
| `special_sweeper` | sp_attack ≥ 300 AND speed ≥ 280 | majority of damaging moves are special |
| `tank` | hp ≥ 300 AND (defense ≥ 200 OR sp_defense ≥ 200) | — |
| `hazard_setter` | — | any move in `HAZARD_SETTER_MOVES` |
| `hazard_removal` | — | any move in `HAZARD_REMOVAL_MOVES` |
| `pivot` | — | any move in `PIVOT_MOVES` |
| `support` | — | any move in `SUPPORT_MOVES` |

---

## Team Validation

**File:** `src/api/services/team_validator.py`

### `TEAM_RULES`

```python
TEAM_RULES = {
    "min_physical_attacker": 1,
    "min_special_attacker":  1,
    "min_tank":              1,
    "min_hazard_setter":     1,
    "min_pivot":             1,
}
```

### `validate_team(builds: list[PokemonBuild]) -> dict`

Aggregates roles across all 6 builds and checks each rule in `TEAM_RULES`.

**Returns:**
```python
{
    "valid": True,          # False if any rule is violated
    "issues": [],           # Human-readable failure messages
    "roles": {              # Count of Pokémon filling each role
        "physical_sweeper": 2,
        "special_sweeper": 1,
        "tank": 1,
        "hazard_setter": 1,
        "hazard_removal": 0,
        "pivot": 1,
        "support": 0,
    }
}
```

---

## Weakness & Resistance Analysis

**File:** `src/api/services/weakness_service.py`

### `analyze_weaknesses(builds: list[PokemonBuild]) -> dict`

Uses `all_multipliers_against(types)` from `type_service` for each build.

- **Weakness**: any type where multiplier > 1.0 for at least one Pokémon. Count = number of team members weak to that type.
- **Resistance**: any type where multiplier < 1.0 (including immunities at 0.0). Count = number of team members that resist.
- Only types with count ≥ 1 appear in the output.

**Returns:**
```python
{
    "weaknesses": {"ice": 3, "rock": 2},
    "resistances": {"steel": 4, "electric": 1}
}
```

---

## Coverage Analysis

**File:** `src/api/services/coverage_service.py`

### `analyze_coverage(builds: list[PokemonBuild]) -> dict`

Collects the type of every non-status move across all 6 builds. For each of the 18 types acting as a defender, checks whether any collected move type is super-effective (multiplier > 1.0).

- `covered_types`: defender types where at least one team move hits super-effectively.
- `missing_types`: the remainder.

**Returns:**
```python
{
    "covered_types": ["grass", "steel", "dragon", "dark"],
    "missing_types": ["water", "fairy", "normal"]
}
```

---

## REST API

**File:** `src/api/routes/team.py`

### `POST /team/analyze`

Accepts a list of 6 `{pokemon_name, set_id}` pairs and returns the full team analysis.

**Request:**
```json
[
  {"pokemon_name": "garchomp",   "set_id": 1},
  {"pokemon_name": "ferrothorn", "set_id": 7},
  {"pokemon_name": "rotom-wash", "set_id": 3},
  {"pokemon_name": "clefable",   "set_id": 2},
  {"pokemon_name": "heatran",    "set_id": 5},
  {"pokemon_name": "landorus-therian", "set_id": 4}
]
```

**Response 200:**
```json
{
  "valid": true,
  "issues": [],
  "roles": {
    "physical_sweeper": 2,
    "special_sweeper": 1,
    "tank": 1,
    "hazard_setter": 1,
    "hazard_removal": 0,
    "pivot": 2,
    "support": 1
  },
  "weaknesses": {"water": 2, "ground": 2},
  "resistances": {"steel": 3, "fire": 2},
  "coverage": {
    "covered_types": ["grass", "steel", "ice", "rock", "dragon"],
    "missing_types": ["water", "fairy"]
  }
}
```

**Response 422** — Team does not have exactly 6 members  
**Response 404** — Set ID not found or does not belong to the named Pokémon

### Pydantic Models (`src/api/models/team.py`)

| Model | Fields |
|---|---|
| `TeamMemberInput` | `pokemon_name` (str), `set_id` (int) |
| `CoverageResult` | `covered_types` (list[str]), `missing_types` (list[str]) |
| `TeamAnalysisResponse` | `valid`, `issues`, `roles`, `weaknesses`, `resistances`, `coverage` |

---

## Testing Strategy

| File | Tests | Approach |
|---|---|---|
| `tests/test_team_loader.py` | 12 | Mock psycopg2 connection; inject synthetic DB rows for set, types, EVs, moves |
| `tests/test_role_service.py` | 21 | Construct `PokemonBuild` directly with known stats/moves; assert returned roles |
| `tests/test_team_validator.py` | 10 | Build teams with known role compositions; assert valid/issues/roles output |
| `tests/test_weakness_service.py` | 6 | Mock `all_multipliers_against`; assert weakness/resistance counts |
| `tests/test_coverage_service.py` | 8 | Mock `all_multipliers_against` and `get_all_attacker_types`; assert covered/missing |
| `tests/test_team_analysis.py` | 10 | Mock all sub-services; verify each is called and results are merged correctly |
| `tests/test_team_api.py` | 11 | FastAPI `TestClient`; mock `load_team` and `analyze_team`; assert response shape and error codes |

**Total: 78 tests**

```bash
pytest tests/test_team_loader.py tests/test_role_service.py tests/test_team_validator.py \
       tests/test_weakness_service.py tests/test_coverage_service.py \
       tests/test_team_analysis.py tests/test_team_api.py -v
```

---

## Files Created / Modified

### New Files

| File | Purpose |
|---|---|
| `src/api/models/team.py` | `MoveDetail`, `PokemonBuild` dataclasses; `TeamMemberInput`, `CoverageResult`, `TeamAnalysisResponse` Pydantic models |
| `src/api/services/team_loader.py` | `load_build` + `load_team` — loads PokemonBuild objects from DB |
| `src/api/services/role_service.py` | Role constants + `detect_roles` |
| `src/api/services/team_validator.py` | `TEAM_RULES` + `validate_team` |
| `src/api/services/weakness_service.py` | `analyze_weaknesses` |
| `src/api/services/coverage_service.py` | `analyze_coverage` |
| `src/api/services/team_analysis.py` | `analyze_team` — thin combiner |
| `src/api/routes/team.py` | `POST /team/analyze` route |
| `tests/test_team_loader.py` | Team loader unit tests |
| `tests/test_role_service.py` | Role detection unit tests |
| `tests/test_team_validator.py` | Team validator unit tests |
| `tests/test_weakness_service.py` | Weakness analysis unit tests |
| `tests/test_coverage_service.py` | Coverage analysis unit tests |
| `tests/test_team_analysis.py` | Combiner unit tests |
| `tests/test_team_api.py` | API integration tests |
| `documentation/sprint_6_documentation.md` | This document |

### Modified Files

| File | Change |
|---|---|
| `src/api/main.py` | Registered `team_router`; added `/team` to root endpoint listing |
| `src/api/routes/__init__.py` | Exported `team_router` |

---

## Summary

Sprint 6 successfully delivered:

1. **Domain model** — `PokemonBuild` and `MoveDetail` dataclasses as the internal representation shared across all services
2. **Team loader** — loads a full build from the DB including computed stats via Sprint 4 `stat_service`
3. **Role detection** — 7 non-exclusive roles detected from stat thresholds and move-name frozensets
4. **Team validator** — configurable `TEAM_RULES` dict; produces human-readable issue messages
5. **Weakness analysis** — aggregates type multipliers across the team; reports per-type counts
6. **Coverage analysis** — determines which of the 18 types the team can threaten with super-effective moves
7. **REST endpoint** — `POST /team/analyze` returning all analysis in one response
8. **78 tests** — all passing, covering all services and the API layer

The system now supports:
- ✅ Pokémon data (Sprint 1)
- ✅ Abilities and relationships (Sprint 1)
- ✅ Types and effectiveness (Sprints 1–3)
- ✅ Moves and learnsets (Sprint 2)
- ✅ Stat calculation with IVs, EVs, Natures (Sprint 4)
- ✅ Competitive sets from Smogon (Sprint 5)
- ✅ Team role analysis, validation, weakness/coverage report (Sprint 6)

---

*Last updated: April 28, 2026*
