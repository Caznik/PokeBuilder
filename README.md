# PokeBuilder

A full-stack VGC (Video Game Championship) Pokémon team-building and analysis platform. Generate, optimize, score, and save competitive Pokémon teams using real Smogon/Pikalytics data and battle replay meta analysis.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS (OKLCH tokens) |
| Routing | React Router v6 |
| Backend | FastAPI + Pydantic v2 + Uvicorn |
| Database | PostgreSQL 16 (psycopg2 connection pool) |
| Testing | pytest + pytest-asyncio (backend) · Vitest + Playwright (frontend) |
| Container | Docker + docker-compose |

---

## Features

- **Pokémon Browser** — paginated list with name/type filters and competitive set viewer
- **Team Builder** — 6-slot builder with autocomplete, set selection, EV overrides, and real-time scoring
- **Team Generator** — guided random generation with include/exclude/regulation constraints
- **Team Optimizer** — genetic algorithm that evolves teams over configurable generations
- **Counter Builder** — beam-search algorithm that builds counter teams against the current regulation meta
- **Team Scoring** — 0–10 aggregate score across five weighted components: coverage, defensive, role, speed control, lead pair
- **Saved Teams** — persist, edit, and compare scored teams per user account
- **Battle Log** — record and filter battle results (Singles / VGC) linked to saved teams
- **Regulations** — manage VGC regulation allowlists; used as filters throughout the app
- **Authentication** — httpOnly cookie-based JWT auth with automatic token rotation

---

## Quick Start

### Docker (recommended)

```bash
docker-compose up
```

Starts PostgreSQL 16 on `:5432` and the FastAPI backend on `:8000`.

**First-time data seed** (run after containers are up):

```bash
docker-compose exec api python -m src.ingestors.seed_natures
docker-compose exec api python -m src.ingestors.type_effectiveness_seeder
docker-compose exec api python -m src.ingestors.pokemon_fetcher
docker-compose exec api python -m src.ingestors.pokemon_types_fetcher
docker-compose exec api python -m src.ingestors.pokemon_abilities_fetcher
docker-compose exec api python -m src.ingestors.pokemon_moves_fetcher
docker-compose exec api python -m src.ingestors.regulations_seeder
docker-compose exec api python -m src.ingestors.vgc_sets_fetcher
```

Then start the frontend dev server separately:

```bash
cd src/frontend && npm install && npm run dev
```

Frontend: `http://localhost:5173` · API: `http://localhost:8000` · Swagger: `http://localhost:8000/docs`

---

### Local Development (without Docker)

**Backend:**

```bash
pip install -e ".[dev]"

export DB_HOST=localhost DB_PORT=5432 DB_NAME=pokebuilder DB_USER=postgres DB_PASSWORD=postgres

uvicorn src.api.main:app --reload
```

**Frontend:**

```bash
cd src/frontend
npm install
npm run dev
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | PostgreSQL hostname |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `pokebuilder` | Database name |
| `DB_USER` | `postgres` | DB username |
| `DB_PASSWORD` | `postgres` | DB password |
| `SMOGON_GEN` | `sv` | Smogon generation slug for set scraping |

---

## Architecture

```
src/frontend/          React SPA (Vite + TypeScript + Tailwind)
      │
      │  HTTP  /api/*
      ▼
src/api/               FastAPI backend (routes → services → DB)
      │
      │  PostgreSQL
      ▼
src/ingestors/         One-off data ingestion scripts (PokeAPI + Smogon + Showdown)
```

**API layering rule:** Routes handle HTTP only. All business logic lives in Services. No SQL in routes, no HTTP in services.

Full architecture, schema, and service documentation lives in `documentation/obsidian/`.

---

## Testing

**Backend:**

```bash
pytest                                                        # all tests
pytest tests/test_team_scorer.py -v                          # single file
pytest tests/test_stat_api.py::TestCalculateEndpoint::test_default_garchomp_calculation -v
```

**Frontend unit tests:**

```bash
cd src/frontend
npm test
```

**E2E (requires both servers running):**

```bash
cd src/frontend
npx playwright test
```

---

## Data Ingest Order

Run ingestors in this sequence to satisfy foreign key dependencies:

```
1.  seed_natures
2.  type_effectiveness_seeder
3.  pokemon_fetcher
4.  pokemon_types_fetcher
5.  pokemon_abilities_fetcher
6.  pokemon_moves_fetcher
7.  regulations_seeder
8.  smogon_sets_fetcher   (or vgc_sets_fetcher)
9.  vgc_sets_fetcher
10. regulation_m_a_fetcher
11. battle_log_fetcher     (daily via cron)
```