# Sprint 5 Documentation

## Overview

This document covers all components created during Sprint 5 of the PokeBuilder project — the Competitive Knowledge Layer. This sprint bridges raw game mechanics and strategic play by sourcing and exposing Smogon competitive sets.

---

## Table of Contents

1. [Feature Overview](#feature-overview)
2. [Database Schema](#database-schema)
3. [Smogon Ingestor](#smogon-ingestor)
4. [Service Layer](#service-layer)
5. [REST API](#rest-api)
6. [Testing Strategy](#testing-strategy)
7. [Files Created / Modified](#files-created--modified)

---

## Feature Overview

Before this sprint the system knew game mechanics (types, stats, moves) but had no strategic context. After this sprint it knows common builds, EV spreads, held items, and moves sourced from Smogon University.

**Core capabilities added:**
- Ingest Smogon competitive sets for any Pokémon and store them in PostgreSQL.
- Expose `GET /competitive-sets/{pokemon_name}` returning all stored sets.
- Normalize Pokémon names between PokeAPI format and Smogon URL slugs.
- Idempotent ingestion — re-running the ingestor replaces existing sets rather than appending duplicates.

---

## Database Schema

### `competitive_sets`

Primary store for a named build. One row per set per Pokémon.

```sql
CREATE TABLE competitive_sets (
    id         SERIAL PRIMARY KEY,
    pokemon_id INTEGER NOT NULL,
    name       TEXT,
    nature_id  INTEGER,
    ability_id INTEGER,
    item       TEXT,
    FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY (nature_id)  REFERENCES natures(id),
    FOREIGN KEY (ability_id) REFERENCES abilities(id)
);
```

### `competitive_set_evs`

One-to-one with `competitive_sets`. Stores the 6 EV values.

```sql
CREATE TABLE competitive_set_evs (
    set_id     INTEGER PRIMARY KEY,
    hp         INTEGER NOT NULL DEFAULT 0,
    attack     INTEGER NOT NULL DEFAULT 0,
    defense    INTEGER NOT NULL DEFAULT 0,
    sp_attack  INTEGER NOT NULL DEFAULT 0,
    sp_defense INTEGER NOT NULL DEFAULT 0,
    speed      INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (set_id) REFERENCES competitive_sets(id) ON DELETE CASCADE
);
```

### `competitive_set_moves`

Junction table linking a set to its moves (up to 4).

```sql
CREATE TABLE competitive_set_moves (
    set_id  INTEGER NOT NULL,
    move_id INTEGER NOT NULL,
    PRIMARY KEY (set_id, move_id),
    FOREIGN KEY (set_id)  REFERENCES competitive_sets(id) ON DELETE CASCADE,
    FOREIGN KEY (move_id) REFERENCES moves(id)
);
```

---

## Smogon Ingestor

**File:** `src/ingestors/smogon_sets_fetcher.py`

### Data Source

Smogon embeds all dex data as a JS variable in each Pokémon's dex page:

```
https://www.smogon.com/dex/sv/pokemon/{slug}/
```

The variable `dexSettings` holds the full JSON. Relevant path:

```
dexSettings.injectRpcs[2][1].strategies[*].movesets[*]
```

Each moveset has: `name`, `natures[]`, `abilities[]`, `items[]`, `moveslots[][]`, `evconfigs[]`.
The first entry in each list is used; move slots use the first alternative per slot.

### Name Translation

PokeAPI names often include form suffixes that Smogon omits from its URL slugs. `_to_smogon_name()` handles the translation:

- **Suffix stripping** — drops standard default-form suffixes (`-incarnate`, `-standard`, `-breed`, `-mask`, `-female`, etc.)
- **Override dict** — handles non-obvious cases:

| DB name | Smogon slug |
|---|---|
| `giratina-altered` | `giratina-origin` |
| `frillish-male` | `frillish` |
| `jellicent-male` | `jellicent` |
| `indeedee-male` | `indeedee` |
| `basculegion-male` | `basculegion` |
| `oinkologne-male` | `oinkologne` |

Pokémon where Smogon uses a gender-specific slug (e.g. `pyroar-male`, `meowstic-male`) are left unchanged and silently produce no sets if Smogon has no page for them.

### Idempotency

Before inserting a batch of sets the ingestor deletes any existing rows for the Pokémon (`DELETE FROM competitive_sets WHERE pokemon_id = %s`). Cascading deletes on `competitive_set_evs` and `competitive_set_moves` clean up child rows automatically.

### Usage

```bash
# Single Pokémon
python -m src.ingestors.smogon_sets_fetcher garchomp

# All Pokémon in the DB
python -m src.ingestors.smogon_sets_fetcher
```

### Key Functions

| Function | Description |
|---|---|
| `_to_smogon_name(db_name)` | Translate PokeAPI name to Smogon URL slug |
| `_fetch_dex_settings(slug)` | Fetch and parse `dexSettings` JSON from Smogon page |
| `_extract_movesets(dex_settings)` | Pull all moveset dicts from parsed JSON |
| `_store_movesets(conn, pokemon_name, movesets)` | Persist sets, EVs, and moves; returns count stored |
| `fetch_and_store(pokemon_name)` | Public entry point for one Pokémon |
| `fetch_and_store_all(pokemon_names)` | Batch mode; skips and logs errors per Pokémon |

---

## Service Layer

**File:** `src/api/services/competitive_service.py`

### `get_sets_for_pokemon(cursor, pokemon_name) -> list[dict]`

Queries all competitive sets for a Pokémon including EVs (via JOIN) and moves (via a per-set query).

**Args:**
- `cursor`: Active psycopg2 cursor
- `pokemon_name`: Case-insensitive Pokémon name

**Returns:** List of set dicts with keys: `id`, `name`, `nature`, `ability`, `item`, `evs`, `moves`

**Raises:** `ValueError` if the Pokémon is not in the DB

**Edge cases:**
- Returns `[]` when the Pokémon exists but has no ingested sets
- `nature`, `ability`, `item` may be `None` for incomplete Smogon entries
- `moves` may be an empty list if no moves resolved against the DB

---

## REST API

**File:** `src/api/routes/competitive.py`

### `GET /competitive-sets/{pokemon_name}`

Returns all stored competitive sets for a Pokémon.

**Response 200:**
```json
{
  "pokemon": "garchomp",
  "sets": [
    {
      "id": 1,
      "name": "Choice Scarf",
      "nature": "jolly",
      "ability": "rough-skin",
      "item": "Choice Scarf",
      "evs": {
        "hp": 0, "attack": 252, "defense": 0,
        "sp_attack": 0, "sp_defense": 4, "speed": 252
      },
      "moves": ["earthquake", "outrage", "stone-edge", "fire-fang"]
    }
  ]
}
```

**Response 200 (no sets ingested):**
```json
{ "pokemon": "magikarp", "sets": [] }
```

**Response 404:** Pokémon not found in DB

**Examples:**
```bash
curl http://localhost:8000/competitive-sets/garchomp
curl http://localhost:8000/competitive-sets/Garchomp   # case-insensitive
```

### Pydantic Models (`src/api/models/competitive.py`)

| Model | Fields |
|---|---|
| `CompetitiveSetEvs` | `hp`, `attack`, `defense`, `sp_attack`, `sp_defense`, `speed` (all int, default 0) |
| `CompetitiveSet` | `id`, `name`, `nature`, `ability`, `item`, `evs`, `moves` |
| `CompetitiveSetResponse` | `pokemon`, `sets` |

---

## Testing Strategy

### `tests/test_competitive_service.py` — Unit tests

Mocks a psycopg2 cursor with pre-programmed `fetchone` / `fetchall` sequences.

| Test | Covers |
|---|---|
| `test_returns_sets_for_known_pokemon` | Full set with EVs and moves |
| `test_returns_empty_sets_when_none_ingested` | Pokémon exists, no sets |
| `test_raises_value_error_for_unknown_pokemon` | Missing Pokémon → ValueError |
| `test_case_insensitive_name` | UPPER-CASE input accepted |
| `test_multiple_sets_returned` | All sets returned, not just first |
| `test_set_with_null_fields` | NULL nature/ability/item returned as None |

### `tests/test_competitive_api.py` — API integration tests

FastAPI `TestClient` with `get_db_cursor` and `get_sets_for_pokemon` mocked at the route level.

| Test | Covers |
|---|---|
| `test_returns_200_with_sets` | Happy path status code |
| `test_response_contains_pokemon_name` | `pokemon` field in response |
| `test_response_contains_sets_list` | `sets` is a list |
| `test_set_has_required_fields` | All fields present |
| `test_evs_has_all_stats` | All 6 EV keys present |
| `test_moves_is_list_of_strings` | Moves are strings |
| `test_returns_200_with_empty_sets_when_none_ingested` | Empty sets list |
| `test_returns_404_for_unknown_pokemon` | 404 + detail message |
| `test_case_insensitive_url` | Mixed-case name accepted |
| `test_ev_values_are_integers` | EV values are ints |

### `tests/test_smogon_sets_fetcher.py` — Name translation unit tests

53 parametrized cases covering suffix stripping, explicit overrides, and no-change pass-throughs.

```bash
pytest tests/test_competitive_service.py tests/test_competitive_api.py tests/test_smogon_sets_fetcher.py -v
```

---

## Files Created / Modified

### New Files

| File | Purpose |
|---|---|
| `resources/sql/tables_schemas/competitive_sets.sql` | DB schema |
| `resources/sql/tables_schemas/competitive_set_evs.sql` | DB schema |
| `resources/sql/tables_schemas/competitive_set_moves.sql` | DB schema |
| `src/ingestors/smogon_sets_fetcher.py` | Smogon ingestor |
| `src/api/models/competitive.py` | Pydantic models |
| `src/api/services/competitive_service.py` | Service layer |
| `src/api/routes/competitive.py` | API route |
| `tests/test_competitive_service.py` | Service unit tests |
| `tests/test_competitive_api.py` | API integration tests |
| `tests/test_smogon_sets_fetcher.py` | Name translation tests |
| `documentation/sprint_5_documentation.md` | This document |

### Modified Files

| File | Change |
|---|---|
| `src/api/main.py` | Registered `competitive_router`; added `/competitive-sets` to root endpoint listing |
| `src/api/routes/__init__.py` | Exported `competitive_router` |
| `src/api/models/__init__.py` | Exported competitive models |
| `src/api/services/__init__.py` | Exported `get_sets_for_pokemon` |

---

## Summary

Sprint 5 successfully delivered:

1. **Three new DB tables** — `competitive_sets`, `competitive_set_evs`, `competitive_set_moves`
2. **Smogon ingestor** — fetches, normalizes, and stores competitive sets with full idempotency
3. **Name translation layer** — handles 30+ PokeAPI → Smogon slug mismatches
4. **REST endpoint** — `GET /competitive-sets/{pokemon_name}` with 404 and empty-set handling
5. **69 tests** — 53 name translation + 10 API + 6 service, all passing

The system now supports:
- ✅ Pokémon data (Sprint 1)
- ✅ Abilities and relationships (Sprint 1)
- ✅ Types and effectiveness (Sprints 1–3)
- ✅ Moves and learnsets (Sprint 2)
- ✅ Stat calculation with IVs, EVs, Natures (Sprint 4)
- ✅ Competitive sets from Smogon (Sprint 5)

---

*Last updated: April 27, 2026*
