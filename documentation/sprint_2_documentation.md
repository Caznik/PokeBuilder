# Sprint 2 Documentation

## Overview

This document provides a comprehensive overview of all components created during Sprint 2 of the PokeBuilder project - focusing on Pokemon Moves.

---

## Table of Contents

1. [Move Data Fetcher](#move-data-fetcher)
2. [Database Schema Updates](#database-schema-updates)
3. [REST API Updates](#rest-api-updates)

---

## Move Data Fetcher

### Pokemon Moves Fetcher (`src/ingestors/pokemon_moves_fetcher.py`)

**Purpose:** Fetches all Pokemon move data from the PokeAPI and stores it in the PostgreSQL database.

**Key Features:**
- Retrieves moves list from `https://pokeapi.co/api/v2/move?limit=1000`
- Parallel fetching with ThreadPoolExecutor (15 workers)
- Extracts comprehensive move data: power, accuracy, PP, type, category, effect
- Maps damage class to move categories (physical/special/status)
- Establishes many-to-many relationship between Pokemon and moves
- Tracks learn method and level for each Pokemon-move relationship
- Idempotent inserts (ON CONFLICT DO UPDATE for moves, ON CONFLICT DO UPDATE for relationships)
- Batch insertion (500 rows per batch) for performance

**Data Extracted:**
- Move ID
- Name
- Type ID (foreign key to types table)
- Power (nullable)
- Accuracy (nullable)
- PP (nullable)
- Category ID (1=physical, 2=special, 3=status)
- Effect description (English)
- Pokemon-Move relationships with learn method and level

**Database Tables:** `moves`, `pokemon_moves`

---

## Database Schema Updates

### New Tables

#### moves
```sql
CREATE TABLE moves (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    type_id INTEGER NOT NULL,
    power INTEGER,
    accuracy INTEGER,
    pp INTEGER,
    category_id INTEGER NOT NULL, -- physical / special / status
    effect TEXT,
    FOREIGN KEY (type_id) REFERENCES types(id),
    FOREIGN KEY (category_id) REFERENCES move_categories(id)
);
```

**Fields:**
- `id`: Primary key (from PokeAPI)
- `name`: Move name (unique)
- `type_id`: Foreign key to types table
- `power`: Base power of the move (nullable for status moves)
- `accuracy`: Accuracy percentage (nullable)
- `pp`: Power Points - number of uses (nullable)
- `category_id`: 1=physical, 2=special, 3=status (foreign key to move_categories)
- `effect`: English description of the move's effect

#### pokemon_moves (Junction Table)
```sql
CREATE TABLE pokemon_moves (
    pokemon_id INTEGER,
    move_id INTEGER,
    learn_method TEXT,  -- level-up / machine / tutor / etc.
    level INTEGER,      -- nullable (only for level-up moves)
    PRIMARY KEY (pokemon_id, move_id, learn_method),
    FOREIGN KEY (pokemon_id) REFERENCES pokemon(id),
    FOREIGN KEY (move_id) REFERENCES moves(id)
);
```

**Fields:**
- `pokemon_id`: Foreign key to pokemon table
- `move_id`: Foreign key to moves table
- `learn_method`: How the Pokemon learns the move (e.g., "level-up", "machine", "tutor")
- `level`: The level at which the Pokemon learns the move (only applicable for level-up moves)

#### move_categories
```sql
CREATE TABLE move_categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

INSERT INTO move_categories (id, name) VALUES
(1, 'physical'),
(2, 'special'),
(3, 'status');
```

**Pre-populated with three categories:**
- Physical: Direct contact moves using Attack/Defense stats
- Special: Energy-based moves using Special Attack/Defense stats
- Status: Non-damaging moves that alter stats, inflict conditions, etc.

---

## REST API Updates

### New Endpoints

#### Move Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/moves/` | List all moves | `page` (int), `page_size` (int), `type_id` (int), `category_id` (int), `name` (str) |
| GET | `/moves/{move_id}` | Get move by ID | `move_id` (path) |
| GET | `/moves/name/{name}` | Get move by name | `name` (path) |

**Response Models:**
- `MoveList`: Paginated list with total count
- `Move`: Basic move data (id, name, type_id, power, accuracy, pp, category_id, effect)
- `MoveDetail`: Complete move data with category info and list of Pokemon that can learn it

#### Move Category Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/moves/categories/` | List all move categories | None |
| GET | `/moves/categories/{category_id}` | Get category by ID | `category_id` (path) |

**Response Models:**
- `MoveCategory`: Move category with id and name

#### Pokemon-Move Relationship Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/moves/pokemon/{pokemon_id}/moves` | Get all moves a Pokemon can learn | `pokemon_id` (path) |

**Response:** Returns Pokemon info with list of all learnable moves including:
- Move details (name, power, accuracy, PP)
- Learn method
- Level (if applicable)
- Category name
- Type name

### Updated Project Structure

```
src/api/
├── main.py                 # Updated with move router
├── db.py                   # Database connection (unchanged)
├── models/
│   ├── __init__.py         # Updated with move models
│   ├── pokemon.py          # (unchanged)
│   ├── ability.py          # (unchanged)
│   ├── type.py             # (unchanged)
│   └── move.py             # NEW: Move Pydantic models
└── routes/
    ├── __init__.py         # Updated with move_router
    ├── pokemon.py          # (unchanged)
    ├── ability.py          # (unchanged)
    ├── type.py             # (unchanged)
    └── move.py             # NEW: Move endpoints
```

### New Pydantic Models

#### MoveCategory
```python
class MoveCategory(BaseModel):
    id: int
    name: str
```

#### Move
```python
class Move(BaseModel):
    id: int
    name: str
    type_id: int
    power: Optional[int] = None
    accuracy: Optional[int] = None
    pp: Optional[int] = None
    category_id: int
    effect: Optional[str] = None
```

#### PokemonMoveEntry
```python
class PokemonMoveEntry(BaseModel):
    pokemon_id: int
    pokemon_name: str
    learn_method: str
    level: Optional[int] = None
```

#### MoveDetail
```python
class MoveDetail(Move):
    category: Optional[MoveCategory] = None
    pokemon: List[PokemonMoveEntry] = []
```

#### MoveList
```python
class MoveList(BaseModel):
    total: int
    items: List[Move]
    page: int
    page_size: int
```

---

## Schema Fix

**Issue Fixed:** In `resources/sql/tables_schemas/moves.sql`, the column was named `category` but the foreign key referenced `category_id`.

**Fix:** Changed column name from `category` to `category_id` for consistency.

```sql
-- Before:
category INTEGER NOT NULL, -- physical / special / status

-- After:
category_id INTEGER NOT NULL, -- physical / special / status
```

---

## Files Created/Modified

### New Files

1. `src/ingestors/pokemon_moves_fetcher.py` - Move data fetcher
2. `src/api/models/move.py` - Move Pydantic models
3. `src/api/routes/move.py` - Move API routes
4. `documentation/sprint_2_documentation.md` - This documentation

### Modified Files

1. `src/api/models/__init__.py` - Added move model imports
2. `src/api/routes/__init__.py` - Added move_router export
3. `src/api/main.py` - Registered move router and updated root endpoint
4. `resources/sql/tables_schemas/moves.sql` - Fixed column name (category → category_id)
5. `documentation/documentation.md` - Added Sprint 2 section

---

## Dependencies

No new dependencies required. Uses existing packages:
- `requests` - HTTP requests to PokeAPI
- `psycopg2-binary` - PostgreSQL database adapter
- `fastapi` - API framework
- `pydantic` - Data validation

---

## Usage

### Running the Move Fetcher

```bash
python src/ingestors/pokemon_moves_fetcher.py
```

### API Endpoints

Once the API is running, the following new endpoints are available:

**List moves:**
```bash
curl http://localhost:8000/moves/
```

**Get move by ID:**
```bash
curl http://localhost:8000/moves/1
```

**Get move by name:**
```bash
curl http://localhost:8000/moves/name/tackle
```

**List move categories:**
```bash
curl http://localhost:8000/moves/categories/
```

**Get Pokemon's moves:**
```bash
curl http://localhost:8000/moves/pokemon/1/moves
```

---

## Summary

Sprint 2 has successfully added:

1. **Move Data Ingestion**: A complete fetcher that retrieves all Pokemon moves, their stats, effects, and relationships from the PokeAPI.

2. **Enhanced Database Schema**: Three new tables supporting moves, move categories, and Pokemon-move relationships with comprehensive data fields.

3. **Extended REST API**: New endpoints for querying moves, filtering by type/category, and retrieving Pokemon's learnable moves with full relationship data.

4. **Complete Documentation**: Comprehensive documentation of all new components, models, and API endpoints.

The system now supports:
- ✅ Pokemon data (from Sprint 1)
- ✅ Abilities and relationships (from Sprint 1)
- ✅ Types (from Sprint 1)
- ✅ Moves and learnsets (NEW in Sprint 2)

This provides a solid foundation for advanced features like team building, move analysis, and battle simulation in future sprints.
