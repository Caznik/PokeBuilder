# Team Save Feature — Design Spec

**Date:** 2026-04-30
**Status:** Approved

---

## Overview

Add the ability to persist a team and its analysis snapshot to the database, browse all saved teams, load them into the Analyzer, edit individual member slots, and delete them.

---

## Database Schema

Two new tables added via SQL migration in `resources/sql/tables_schemas/`.

### `saved_teams`

| column       | type                          | notes                        |
|--------------|-------------------------------|------------------------------|
| `id`         | `SERIAL PRIMARY KEY`          |                              |
| `name`       | `TEXT NOT NULL`               | user-given label             |
| `score`      | `NUMERIC(5,2)`                | snapshot at save time        |
| `analysis`   | `JSONB NOT NULL`              | full `TeamAnalysisResponse`  |
| `created_at` | `TIMESTAMPTZ DEFAULT now()`   |                              |

### `saved_team_members`

| column         | type                                                       | notes                        |
|----------------|------------------------------------------------------------|------------------------------|
| `id`           | `SERIAL PRIMARY KEY`                                       |                              |
| `team_id`      | `INTEGER REFERENCES saved_teams(id) ON DELETE CASCADE`     | cascade deletes members      |
| `slot`         | `SMALLINT NOT NULL`                                        | 0–5, preserves member order  |
| `pokemon_name` | `TEXT NOT NULL`                                            |                              |
| `set_id`       | `INTEGER REFERENCES competitive_sets(id)`                  |                              |

Cascade delete on `team_id` ensures member rows are cleaned up when a team is removed.

---

## API Layer

New route group registered in `main.py` as `saved_teams_router` with prefix `/saved-teams`.

### Endpoints

| Method   | Path                                  | Description                                                         |
|----------|---------------------------------------|---------------------------------------------------------------------|
| `POST`   | `/saved-teams/`                       | Save a new team                                                     |
| `GET`    | `/saved-teams/`                       | List all saved teams (summary, no analysis)                         |
| `GET`    | `/saved-teams/{id}`                   | Fetch a single team with full analysis                              |
| `PATCH`  | `/saved-teams/{id}`                   | Update team name and/or refresh score+analysis snapshot             |
| `PATCH`  | `/saved-teams/{id}/members/{slot}`    | Swap a single member slot; re-scores team and returns fresh detail  |
| `DELETE` | `/saved-teams/{id}`                   | Delete team and cascade-remove its members                          |

### Models (`src/api/models/saved_team.py`)

- **`SaveTeamRequest`** — `name: str`, `members: list[TeamMemberInput]` (exactly 6), `score: float`, `analysis: TeamAnalysisResponse`
- **`UpdateTeamRequest`** — `name: str | None`, `score: float | None`, `analysis: TeamAnalysisResponse | None` (all optional; at least one must be provided — 422 if all are None)
- **`UpdateMemberRequest`** — `pokemon_name: str`, `set_id: int`
- **`SavedTeamSummary`** — `id`, `name`, `score`, `created_at`, `members: list[TeamMemberInput]`
- **`SavedTeamDetail`** — extends `SavedTeamSummary` with `analysis: TeamAnalysisResponse`

### Service (`src/api/services/saved_team_service.py`)

Thin DB layer following existing pattern (receives `conn` from the route):

- `save_team(conn, name, members, score, analysis) -> SavedTeamDetail`
- `list_teams(conn) -> list[SavedTeamSummary]`
- `get_team(conn, id) -> SavedTeamDetail`
- `update_team(conn, id, name?, score?, analysis?) -> SavedTeamDetail`
- `update_member(conn, id, slot, pokemon_name, set_id) -> SavedTeamDetail` — updates the slot, then re-loads, re-scores, and re-analyzes the full team, returning a fresh `SavedTeamDetail`
- `delete_team(conn, id) -> None`

---

## Frontend

### New page: `SavedTeams.tsx`

- Added to the Navbar as "Saved Teams"
- Fetches `GET /saved-teams/` on mount
- Renders each team using `TeamResultCard` (reused as-is)
- Each card has two extra action buttons:
  - **Load** — navigates to `/analyze` and populates the Analyzer with the team's members
  - **Delete** — shows an inline confirmation, then calls `DELETE /saved-teams/{id}` and removes the card from local state
- Member slots are editable inline: clicking a slot opens a `PokemonNameInput` + set selector; confirming calls `PATCH /saved-teams/{id}/members/{slot}` and updates local state with the returned fresh analysis

### Save button on Generator and Optimizer

- `TeamResultCard` gains an optional `onSave?: (name: string) => void` prop
- When provided, a "Save" button appears in the card header
- Clicking it reveals a small inline text input for the team name; confirming calls `POST /saved-teams/` with the card's existing `members`, `score`, and `analysis`

### API client additions (`src/frontend/src/api/client.ts`)

```ts
savedTeams: {
  list: () => Promise<SavedTeamSummary[]>
  get: (id: number) => Promise<SavedTeamDetail>
  save: (payload: SaveTeamRequest) => Promise<SavedTeamDetail>
  update: (id: number, payload: UpdateTeamRequest) => Promise<SavedTeamDetail>
  updateMember: (id: number, slot: number, member: TeamMemberInput) => Promise<SavedTeamDetail>
  delete: (id: number) => Promise<void>
}
```

### New TypeScript types (`src/frontend/src/api/types.ts`)

- `SaveTeamRequest`
- `UpdateTeamRequest`
- `SavedTeamSummary`
- `SavedTeamDetail`

---

## Error Handling

- `POST /saved-teams/` with `members.length !== 6` → 422
- `GET/PATCH/DELETE /saved-teams/{id}` with unknown id → 404
- `PATCH /saved-teams/{id}/members/{slot}` with `slot` outside 0–5 → 422
- `PATCH /saved-teams/{id}/members/{slot}` with unknown `pokemon_name` or `set_id` → 404 (re-uses existing `load_team` validation)

---

## Testing

- **Backend unit tests** (`tests/test_saved_team_api.py`) — one test per endpoint covering happy path and error cases (missing id, bad slot, wrong member count)
- **Service tests** (`tests/test_saved_team_service.py`) — test `save_team`, `list_teams`, `get_team`, `update_team`, `update_member`, `delete_team` with a real DB connection (following existing test patterns)
- **Frontend** — manual verification: save a team from Generator, view it in Saved Teams, swap a member slot, load into Analyzer, delete
