# Sprint 1 Documentation

## Overview

This document provides a comprehensive overview of all components created during Sprint 1 of the PokeBuilder project.

---

## Table of Contents

1. [Data Fetchers](#data-fetchers)
2. [Database Schema](#database-schema)
3. [REST API](#rest-api)

---

## Data Fetchers

### 1. Pokemon Fetcher (`src/ingestors/pokemon_fetcher.py`)

**Purpose:** Fetches all Pokemon data from the PokeAPI and stores it in the PostgreSQL database.

**Key Features:**
- Retrieves Pokemon list from `https://pokeapi.co/api/v2/pokemon?limit=10000`
- Parallel fetching with ThreadPoolExecutor (20 workers)
- Extracts comprehensive stats: HP, Attack, Defense, Special Attack, Special Defense, Speed
- Parses generation information from species data
- Idempotent inserts (ON CONFLICT DO NOTHING)
- Batch insertion (100 rows per batch) for performance

**Data Extracted:**
- Pokemon ID
- Name
- Generation
- Base stats (HP, Attack, Defense, Special Attack, Special Defense, Speed)

**Database Table:** `pokemon`

---

### 2. Pokemon Abilities Fetcher (`src/ingestors/pokemon_abilities_fetcher.py`)

**Purpose:** Fetches all Pokemon abilities and their relationships from the PokeAPI.

**Key Features:**
- Retrieves abilities from `https://pokeapi.co/api/v2/ability?limit=1000`
- Parallel fetching with ThreadPoolExecutor (15 workers)
- Extracts English descriptions from effect_entries or effect_changes
- Establishes many-to-many relationship between Pokemon and abilities
- Tracks whether ability is hidden
- Idempotent inserts with batch processing

**Data Extracted:**
- Ability ID
- Name
- Description (English)
- Pokemon-ability relationships (with is_hidden flag)

**Database Tables:** `abilities`, `pokemon_abilities`

---

### 3. Pokemon Types Fetcher (`src/ingestors/pokemon_types_fetcher.py`)

**Purpose:** Fetches all Pokemon types from the PokeAPI.

**Key Features:**
- Retrieves types from `https://pokeapi.co/api/v2/type?limit=1000`
- Parallel fetching with ThreadPoolExecutor (10 workers)
- Simple data extraction (ID and name only)
- Idempotent inserts

**Data Extracted:**
- Type ID
- Name

**Database Table:** `types`

---

## Database Schema

### Tables Overview

```
pokemon
├── id (PRIMARY KEY)
├── name (UNIQUE, NOT NULL)
├── generation (INTEGER, nullable)
├── base_hp (INTEGER, NOT NULL)
├── base_attack (INTEGER, NOT NULL)
├── base_defense (INTEGER, NOT NULL)
├── base_sp_attack (INTEGER, NOT NULL)
├── base_sp_defense (INTEGER, NOT NULL)
└── base_speed (INTEGER, NOT NULL)

abilities
├── id (PRIMARY KEY)
├── name (TEXT, NOT NULL)
└── description (TEXT, nullable)

types
├── id (PRIMARY KEY)
└── name (TEXT, NOT NULL, UNIQUE)

pokemon_abilities (Junction Table)
├── pokemon_id (FOREIGN KEY → pokemon.id)
├── ability_id (FOREIGN KEY → abilities.id)
└── is_hidden (BOOLEAN, NOT NULL)

pokemon_types (Junction Table)
├── pokemon_id (FOREIGN KEY → pokemon.id)
├── type_id (FOREIGN KEY → types.id)
└── slot (INTEGER, NOT NULL)
```

### Schema Details

#### pokemon
```sql
CREATE TABLE pokemon (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    generation INTEGER,
    base_hp INTEGER NOT NULL,
    base_attack INTEGER NOT NULL,
    base_defense INTEGER NOT NULL,
    base_sp_attack INTEGER NOT NULL,
    base_sp_defense INTEGER NOT NULL,
    base_speed INTEGER NOT NULL
);
```

#### abilities
```sql
CREATE TABLE abilities (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
);
```

#### types
```sql
CREATE TABLE types (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
```

#### pokemon_abilities
```sql
CREATE TABLE pokemon_abilities (
    pokemon_id INTEGER,
    ability_id INTEGER,
    is_hidden BOOLEAN NOT NULL,
    PRIMARY KEY (pokemon_id, ability_id),
    FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY (ability_id) REFERENCES abilities(id)
);
```

#### pokemon_types
```sql
CREATE TABLE pokemon_types (
    pokemon_id INTEGER,
    type_id INTEGER,
    slot INTEGER NOT NULL,
    PRIMARY KEY (pokemon_id, slot),
    FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY (type_id) REFERENCES types(id)
);
```

---

## REST API

### Framework & Dependencies

- **FastAPI** - Modern, fast web framework for building APIs
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation and serialization
- **psycopg2** - PostgreSQL database adapter
- **ThreadPoolExecutor** - Connection pooling

### Project Structure

```
src/api/
├── __init__.py
├── main.py                 # FastAPI application entry point
├── db.py                   # Database connection & session management
├── models/
│   ├── __init__.py
│   ├── pokemon.py          # Pokemon Pydantic models
│   ├── ability.py          # Ability Pydantic models
│   └── type.py             # Type Pydantic models
└── routes/
    ├── __init__.py
    ├── pokemon.py          # Pokemon endpoints
    ├── ability.py          # Ability endpoints
    └── type.py             # Type endpoints
```

### API Endpoints

#### Pokemon Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/pokemon/` | List all Pokemon | `page` (int), `page_size` (int), `generation` (int), `name` (str) |
| GET | `/pokemon/{pokemon_id}` | Get Pokemon by ID | `pokemon_id` (path) |
| GET | `/pokemon/name/{name}` | Get Pokemon by name | `name` (path) |

**Response Models:**
- `PokemonList` - Paginated list with total count
- `PokemonDetail` - Complete Pokemon data with abilities and types

#### Ability Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/abilities/` | List all abilities | `name` (query, optional) |
| GET | `/abilities/{ability_id}` | Get ability by ID | `ability_id` (path) |
| GET | `/abilities/name/{name}` | Get ability by name | `name` (path) |

**Response Models:**
- `Ability` - Basic ability info
- `AbilityDetail` - Ability with related Pokemon list

#### Type Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/types/` | List all types | None |
| GET | `/types/{type_id}` | Get type by ID | `type_id` (path) |
| GET | `/types/name/{name}` | Get type by name | `name` (path) |
| GET | `/types/{type_id}/pokemon` | Get Pokemon by type | `type_id` (path) |

**Response Models:**
- `Type` - Basic type info
- `TypeDetail` - Type with Pokemon count

### Security Features

- **SQL Injection Prevention**: All queries use parameterized statements (`%s` placeholders)
- **Input Validation**: Pydantic models validate all request data
- **Pagination**: Limits prevent excessive data retrieval (max 100 items per page)
- **CORS**: Configured to allow cross-origin requests (for development)

### Docker Configuration

**Dockerfile** (`Dockerfile`):
- Based on `python:3.12-slim`
- Installs system dependencies (gcc, postgresql-client)
- Installs Python requirements
- Exposes port 8000
- Runs with Uvicorn

**Docker Compose** (`docker-compose.yml`):
```yaml
services:
  postgres:
    image: postgres:16
    # ... database configuration
  
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DB_HOST: postgres
      DB_PORT: 5432
      DB_NAME: pokebuilder
      DB_USER: postgres
      DB_PASSWORD: postgres
    depends_on:
      - postgres
    command: uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Running the API

**Development Mode (with auto-reload):**
```bash
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Production Mode:**
```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**With Docker:**
```bash
docker compose up api
```

### API Documentation

Once running, interactive API documentation is available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

---

## Dependencies

### Python Packages

```
requests>=2.31.0
psycopg2-binary>=2.9.9
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0
```

### System Requirements

- Python 3.12+
- PostgreSQL 16+
- Docker & Docker Compose (optional)

---

## Summary

Sprint 1 has successfully established:

1. **Data Ingestion Pipeline**: Three fetchers that extract Pokemon, abilities, and types data from the PokeAPI and store it in a normalized PostgreSQL database.

2. **Database Schema**: Five tables with proper relationships, foreign keys, and constraints to support complex queries.

3. **REST API**: A complete FastAPI application with endpoints for querying all ingested data, including pagination, filtering, and relationship traversal.

4. **Containerization**: Docker configuration for easy deployment and development.

The system is now ready for data ingestion and API consumption. Future sprints can build upon this foundation to add features like team building, battle simulation, or advanced search capabilities.
