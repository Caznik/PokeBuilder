# Sprint 11 Documentation — Save Teams Feature

**Sprint goal:** Allow users to persist generated and optimized teams to the database, view and manage them on a dedicated Saved Teams page, inline-edit team members, and load a saved team directly into the Team Analyzer.

---

## Overview

Sprint 11 introduced the complete Save Teams feature across the full stack: PostgreSQL schema, backend service, REST API, and React frontend.

### Key capabilities delivered

- Save any generated or optimized team (with score, breakdown, and analysis snapshot) under a custom name
- List all saved teams on a dedicated `/saved` page
- Inline slot-level editing: swap any member's Pokémon or competitive set and have the team automatically re-scored
- Delete teams with a confirmation step
- Load a saved team into the Team Analyzer with all 6 slots pre-filled

---

## Database Schema

Two new tables — no ORM, raw SQL scripts in `resources/sql/tables_schemas/`.

### `saved_teams`

```sql
CREATE TABLE IF NOT EXISTS saved_teams (
    id          SERIAL PRIMARY KEY,
    name        TEXT            NOT NULL,
    score       NUMERIC(5, 2)   NOT NULL,
    breakdown   JSONB           NOT NULL,
    analysis    JSONB           NOT NULL,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT now()
);
```

`breakdown` and `analysis` are snapshot JSONB columns so the Saved Teams page can render full details without extra API calls.

### `saved_team_members`

```sql
CREATE TABLE IF NOT EXISTS saved_team_members (
    id           SERIAL   PRIMARY KEY,
    team_id      INTEGER  NOT NULL REFERENCES saved_teams(id) ON DELETE CASCADE,
    slot         SMALLINT NOT NULL CHECK (slot BETWEEN 0 AND 5),
    pokemon_name TEXT     NOT NULL,
    set_id       INTEGER  NOT NULL REFERENCES competitive_sets(id),
    UNIQUE (team_id, slot)
);
```

Slot-level uniqueness enables targeted PATCH updates. `ON DELETE CASCADE` keeps members in sync when a team is deleted.

---

## Backend

### Models (`src/api/models/saved_team.py`)

Six Pydantic v2 models:

| Model | Purpose |
|---|---|
| `SaveTeamRequest` | POST body; validates name is non-empty and members list is exactly 6 |
| `UpdateTeamRequest` | PATCH body; all fields optional; `has_update()` guards against no-op calls |
| `UpdateMemberRequest` | PATCH body for a single slot |
| `SavedTeamMember` | Denormalized member row (name, set_id, set_name, nature, ability) |
| `SavedTeamSummary` | List response shape (id, name, score, created_at, members) |
| `SavedTeamDetail` | Extends Summary with breakdown + analysis |

### Service (`src/api/services/saved_team_service.py`)

Six public functions following the project's three-tier pattern:

| Function | Description |
|---|---|
| `save_team` | INSERT saved_teams + 6 member rows; commits; returns full detail via `_load_members` |
| `list_teams` | SELECT all teams; `_load_members` called inside a single cursor (no N+1) |
| `get_team` | SELECT by id; raises `ValueError("not found")` for 404 propagation |
| `update_team` | Dynamic SET clause for name-only updates; raises `ValueError` if not found |
| `update_member` | UPDATE slot; re-runs `load_team` → `analyze_team` → `score_team`; persists new score/breakdown/analysis |
| `delete_team` | DELETE; checks `rowcount == 0` for 404 |

`_load_members` JOINs `competitive_sets`, `natures`, and `abilities` so `SavedTeamMember` is display-ready without additional queries.

### Routes (`src/api/routes/saved_teams.py`)

Six REST endpoints:

| Method | Path | Status | Description |
|---|---|---|---|
| POST | `/saved-teams/` | 201 | Save a new team |
| GET | `/saved-teams/` | 200 | List all saved teams (summaries) |
| GET | `/saved-teams/{id}` | 200 | Get full team detail |
| PATCH | `/saved-teams/{id}` | 200 | Update team name |
| PATCH | `/saved-teams/{id}/members/{slot}` | 200 | Swap one member and re-score |
| DELETE | `/saved-teams/{id}` | 204 | Delete a team |

All routes return 404 on `ValueError` from the service.

---

## Tests

### Service tests (`tests/test_saved_team_service.py`)

13 unit tests across 6 classes. All DB calls are mocked via `MagicMock` with an explicit `mock_cursor.rowcount` integer (not a MagicMock attribute) to ensure `rowcount == 0` comparisons work correctly.

| Class | Tests | What's covered |
|---|---|---|
| `TestSaveTeam` | 3 | Returns `SavedTeamDetail`, executes 8 SQL statements (1 team + 6 members + 1 load), commits once |
| `TestListTeams` | 2 | Returns `list[SavedTeamSummary]`, handles empty DB |
| `TestGetTeam` | 2 | Returns `SavedTeamDetail`, raises `ValueError` when not found |
| `TestUpdateTeam` | 2 | Updates name field, raises `ValueError` when not found |
| `TestUpdateMember` | 2 | Re-scores team after slot swap, raises `ValueError` when not found |
| `TestDeleteTeam` | 2 | Executes DELETE + commit, raises `ValueError` when not found |

### API tests (`tests/test_saved_team_api.py`)

15 integration tests using FastAPI `TestClient`. Both `get_db_connection` and service functions are mocked at the route module level.

| Class | Tests | What's covered |
|---|---|---|
| `TestSaveTeamEndpoint` | 3 | 201 response, correct payload forwarding, 422 on empty name |
| `TestListTeamsEndpoint` | 2 | 200 with list, 200 with empty list |
| `TestGetTeamEndpoint` | 2 | 200 with detail, 404 on ValueError |
| `TestUpdateTeamEndpoint` | 3 | 200 on valid patch, 404 on not found, 422 on no-op request |
| `TestUpdateMemberEndpoint` | 3 | 200 on slot swap, 404 on not found, 422 on slot > 5 |
| `TestDeleteTeamEndpoint` | 2 | 204 on success, 404 on not found |

**Total new tests: 28**

```bash
pytest tests/test_saved_team_service.py tests/test_saved_team_api.py -v
```

---

## Frontend

### New types (`src/frontend/src/api/types.ts`)

Six new TypeScript interfaces: `SavedTeamMember`, `SavedTeamSummary`, `SavedTeamDetail`, `SaveTeamRequest`, `UpdateTeamRequest`, `UpdateMemberRequest`.

### API client (`src/frontend/src/api/client.ts`)

Added `patch<T>()` and `del()` HTTP helpers. Added `api.savedTeams` namespace with `list`, `get`, `save`, `update`, `updateMember`, `delete`.

### Components modified

**`TeamResultCard`** — Optional `onSave?: (name: string) => Promise<void>` prop. When provided, a "Save" button appears in the card header. Clicking it reveals an inline text input for the team name. On confirm, calls `onSave` and transitions the button to a "Saved ✓" state.

### New pages

**`SavedTeams` (`src/frontend/src/pages/SavedTeams.tsx`)** — Dedicated page at `/saved` showing all saved teams. Each team card has:
- Member chips sorted by slot
- Collapsible ScoreBreakdown and AnalysisReport
- "Load into Analyzer" button (navigates to `/analyze` with members in router state)
- Inline slot editor: click a slot to swap Pokémon name and set ID; saves immediately on confirm
- Delete button with confirmation step

### Navigation wired

- `Navbar.tsx` — added "Saved Teams" link pointing to `/saved`
- `App.tsx` — registered `<Route path="/saved" element={<SavedTeams />} />`
- `TeamGenerator.tsx` — passes `onSave` closure to each `TeamResultCard`
- `TeamOptimizer.tsx` — same as Generator
- `TeamAnalyzer.tsx` — reads `location.state?.members` on mount; if present, populates all 6 slots and fetches their competitive sets automatically

---

## Files Created / Modified

### New Files

| File | Purpose |
|---|---|
| `resources/sql/tables_schemas/saved_teams.sql` | `saved_teams` table DDL |
| `resources/sql/tables_schemas/saved_team_members.sql` | `saved_team_members` table DDL with CASCADE and slot constraint |
| `src/api/models/saved_team.py` | 6 Pydantic v2 request/response models |
| `src/api/services/saved_team_service.py` | Full CRUD service with re-scoring on member update |
| `src/api/routes/saved_teams.py` | 6 REST endpoints |
| `src/frontend/src/pages/SavedTeams.tsx` | Saved Teams page with inline editing |
| `tests/test_saved_team_service.py` | 13 service unit tests |
| `tests/test_saved_team_api.py` | 15 API integration tests |
| `documentation/sprint_11_documentation.md` | This document |

### Modified Files

| File | Change |
|---|---|
| `src/api/routes/__init__.py` | Exported `saved_teams_router` |
| `src/api/main.py` | Registered `saved_teams_router` |
| `src/frontend/src/api/types.ts` | Added 6 saved-team interfaces |
| `src/frontend/src/api/client.ts` | Added `patch`, `del` helpers and `api.savedTeams` |
| `src/frontend/src/components/TeamResultCard.tsx` | Added optional `onSave` prop and inline save UI |
| `src/frontend/src/components/Navbar.tsx` | Added "Saved Teams" nav link |
| `src/frontend/src/App.tsx` | Registered `/saved` route |
| `src/frontend/src/pages/TeamGenerator.tsx` | Passes `onSave` to TeamResultCard |
| `src/frontend/src/pages/TeamOptimizer.tsx` | Passes `onSave` to TeamResultCard |
| `src/frontend/src/pages/TeamAnalyzer.tsx` | Pre-fills slots from router state |

---

## Summary

Sprint 11 delivered the full Save Teams feature end-to-end:

1. **Normalized PostgreSQL schema** — slot-level granularity enables targeted member updates without replacing the entire team record
2. **JSONB snapshots** — `breakdown` and `analysis` stored at save time so the Saved Teams page renders full detail with a single query per team
3. **Auto re-scoring** — swapping a member triggers `load_team → analyze_team → score_team` and persists the updated score, breakdown, and analysis atomically
4. **28 new tests** — covering full CRUD lifecycle, error paths, and HTTP status codes
5. **Seamless frontend flow** — save from Generator/Optimizer → manage on Saved Teams page → load into Analyzer with all slots pre-filled

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
- ✅ VGC doubles migration — analysis layer updated to doubles format (Sprint 10)
- ✅ Save, manage, and load teams — full persistence layer with inline editing (Sprint 11)

---

*Last updated: April 30, 2026*
