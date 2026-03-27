# Sprint 3 Documentation

## Overview

This document provides a comprehensive overview of all components created during Sprint 3 of the PokeBuilder project - focusing on the Type Effectiveness Engine, the foundational intelligence layer for battle calculations.

---

## Table of Contents

1. [Type Effectiveness Engine](#type-effectiveness-engine)
2. [Database Schema Updates](#database-schema-updates)
3. [Service Layer](#service-layer)
4. [REST API Updates](#rest-api-updates)
5. [Testing Strategy](#testing-strategy)

---

## Type Effectiveness Engine

### Purpose

The Type Effectiveness Engine is the core intelligence layer that powers all type-based calculations. It provides O(1) lookups for damage multipliers, enabling:

- Damage calculation
- Team weakness detection
- Coverage scoring
- Counter-team generation

### Key Features

- **In-Memory Caching**: Full type effectiveness matrix loaded once at startup
- **O(1) Lookups**: Direct dictionary access for all multiplier queries
- **Dual-Type Support**: Multiplies individual type multipliers for Pokemon with two types
- **Future-Proof Design**: `all_multipliers_against()` function powers coverage analysis

### Data Flow

```
Database (type_effectiveness table)
    ↓ (loaded once at startup)
In-Memory Matrix Dict[(attacker_id, defender_id)] → multiplier
    ↓
Service Functions (O(1) lookups)
    ↓
API Endpoints
```

### Type Effectiveness Chart

The complete 18×18 type effectiveness matrix includes:

| Multiplier | Meaning | Examples |
|------------|---------|----------|
| 2.0 | Super effective | Fire → Grass, Water → Fire |
| 1.0 | Neutral | Most type combinations |
| 0.5 | Not very effective | Fire → Water, Grass → Fire |
| 0.0 | No effect | Normal → Ghost, Electric → Ground |

**Example Calculations:**
- Fire vs Grass = 2.0
- Fire vs Water = 0.5
- Fire vs Grass/Steel = 2.0 × 2.0 = 4.0
- Electric vs Ground = 0.0
- Normal vs Ghost = 0.0

---

## Database Schema Updates

### New Table

#### type_effectiveness

```sql
CREATE TABLE type_effectiveness (
    attacker_type_id INTEGER,
    defender_type_id INTEGER,
    multiplier REAL NOT NULL,
    PRIMARY KEY (attacker_type_id, defender_type_id),
    FOREIGN KEY (attacker_type_id) REFERENCES types(id),
    FOREIGN KEY (defender_type_id) REFERENCES types(id)
);
```

**Fields:**
- `attacker_type_id`: Foreign key to the attacking type
- `defender_type_id`: Foreign key to the defending type
- `multiplier`: Damage multiplier (2.0, 1.0, 0.5, or 0.0)

**Note:** Missing relationships default to 1.0 (neutral) in the service layer.

---

## Service Layer

### Type Effectiveness Seeder (`src/ingestors/type_effectiveness_seeder.py`)

**Purpose:** Seeds the `type_effectiveness` table with the complete Pokemon type effectiveness chart.

**Key Features:**
- Clean-install approach (no ON CONFLICT handling)
- Queries `types` table for name→ID mapping
- Bulk inserts all effectiveness relationships
- Includes all 18 Pokemon types

**Usage:**
```bash
python -m src.ingestors.type_effectiveness_seeder
```

**Data Source:** The complete TYPE_CHART constant includes all type relationships as specified in the Pokemon games.

---

### Type Service (`src/api/services/type_service.py`)

**Purpose:** Core type effectiveness calculation engine with in-memory caching.

**Key Features:**
- Lazy loading of type matrix on first use
- O(1) dictionary lookups for all queries
- Supports both type names and type IDs
- Dual-type calculation (multiplies individual multipliers)
- Future-proof `all_multipliers_against()` function

**Core Functions:**

#### `get_type_id(name)`
```python
def get_type_id(name: Union[str, int]) -> int:
    """Resolve a type name to its ID."""
```
- Accepts type name (case-insensitive) or ID
- Returns type ID
- Raises `ValueError` for unknown types

#### `get_multiplier(move_type, defender_type)`
```python
def get_multiplier(
    move_type: Union[str, int],
    defender_type: Union[str, int]
) -> float:
    """Get damage multiplier for single type matchup."""
```
- Returns 2.0, 1.0, 0.5, or 0.0
- Defaults to 1.0 for undefined relationships
- O(1) lookup from in-memory matrix

#### `calculate_damage_multiplier(move_type, defender_types)`
```python
def calculate_damage_multiplier(
    move_type: Union[str, int],
    defender_types: Sequence[Union[str, int]]
) -> float:
    """Calculate final damage multiplier against Pokemon."""
```
- Handles single or dual-type defenders
- Multiplies individual type multipliers
- Returns final damage multiplier

#### `all_multipliers_against(defender_types)`
```python
def all_multipliers_against(
    defender_types: Sequence[Union[str, int]]
) -> Dict[str, float]:
    """Get all damage multipliers for all attacking types."""
```
- Returns dict mapping attacker type names to multipliers
- Powers coverage analysis and team weakness detection
- **Future Use:** Team scoring, coverage analysis, AI optimization

**Performance:**
- Matrix loaded once at startup (≈300 rows)
- All lookups are O(1) dictionary access
- No database queries during API requests

---

## REST API Updates

### New Endpoints

#### Type Effectiveness Endpoints

| Method | Endpoint | Description | Parameters |
|--------|----------|-------------|------------|
| GET | `/types/multiplier` | Get damage multiplier | `move` (type name), `defender` (comma-separated types) |
| GET | `/types/multipliers` | Get all multipliers vs defender | `defender` (comma-separated types) |

**Examples:**

```bash
# Fire vs Grass = 2.0
curl "http://localhost:8000/types/multiplier?move=fire&defender=grass"
# Response: {"multiplier": 2.0}

# Fire vs Grass/Steel = 4.0
curl "http://localhost:8000/types/multiplier?move=fire&defender=grass,steel"
# Response: {"multiplier": 4.0}

# Electric vs Ground = 0.0
curl "http://localhost:8000/types/multiplier?move=electric&defender=ground"
# Response: {"multiplier": 0.0}

# Get all attacker multipliers vs Grass/Steel
curl "http://localhost:8000/types/multipliers?defender=grass,steel"
# Response: {"multipliers": {"fire": 4.0, "water": 1.0, ...}}
```

### Response Models

#### MultiplierResponse
```python
class MultiplierResponse(BaseModel):
    multiplier: float
```

#### AllMultipliersResponse
```python
class AllMultipliersResponse(BaseModel):
    multipliers: Dict[str, float]
```

### Updated Project Structure

```
src/api/
├── main.py                 # Updated with type effectiveness router
├── services/               # NEW: Service layer
│   ├── __init__.py
│   └── type_service.py     # Type effectiveness engine
├── models/
│   └── type.py             # Updated with response models
└── routes/
    └── type.py             # Updated with multiplier endpoints
```

---

## Testing Strategy

### Unit Tests (`tests/test_type_service.py`)

**Purpose:** Test service layer functions with synthetic data (no database required).

**Approach:**
- Monkey-patch service module with synthetic matrix
- Test all core functions independently
- Verify dual-type calculations
- Test edge cases and error conditions

**Test Coverage:**

| Test Class | Cases Covered |
|------------|---------------|
| TestGetMultiplier | Fire vs Grass (2.0), Fire vs Water (0.5), Normal vs Ghost (0.0), Electric vs Ground (0.0), neutral damage, missing relationships, ID-based lookups |
| TestCalculateDamageMultiplier | Single type, dual-type super effective (4.0), dual-type resisted (0.0), normal/rock/steel combo (0.25) |
| TestAllMultipliersAgainst | All attacker types returned, Grass weaknesses, Ghost immunity, dual-type defender calculations |
| TestGetTypeId | Name resolution, ID passthrough, case insensitivity, error handling |
| TestGetTypeName | ID to name resolution, error handling |
| TestEdgeCases | Empty defender types, triple-type combos, very resistant combos |

**Run Tests:**
```bash
pytest tests/test_type_service.py -v
```

### API Integration Tests (`tests/test_type_api.py`)

**Purpose:** Test FastAPI endpoints with TestClient using synthetic data.

**Approach:**
- Inject synthetic matrix into service before creating TestClient
- Test all endpoint variations
- Verify response formats and error handling
- Test case insensitivity and parameter validation

**Test Coverage:**

| Test Class | Cases Covered |
|------------|---------------|
| TestMultiplierEndpoint | All required cases (Fire vs Grass, Fire vs Water, Normal vs Ghost, Electric vs Ground, Fire vs Grass/Steel), case insensitivity, invalid types, missing parameters |
| TestMultipliersEndpoint | All attackers returned, Ghost immunity, Grass weaknesses, dual-type defender, invalid types, missing parameters |
| TestEndpointResponseFormat | Response structure, data types |
| TestEdgeCases | Whitespace handling, very resistant combos, immunity chains |

**Run Tests:**
```bash
pytest tests/test_type_api.py -v
```

### Required Test Cases (from Sprint Requirements)

| Case | Expected | Status |
|------|----------|--------|
| Fire vs Grass | 2.0 | ✅ Pass |
| Fire vs Water | 0.5 | ✅ Pass |
| Normal vs Ghost | 0.0 | ✅ Pass |
| Electric vs Ground | 0.0 | ✅ Pass |
| Fire vs Grass/Steel | 4.0 | ✅ Pass |

---

## Files Created/Modified

### New Files

1. `resources/sql/tables_schemas/type_effectiveness.sql` - Type effectiveness table schema
2. `src/ingestors/type_effectiveness_seeder.py` - Database seeder script
3. `src/api/services/__init__.py` - Service exports
4. `src/api/services/type_service.py` - Core effectiveness engine
5. `tests/test_type_service.py` - Unit tests with synthetic data
6. `tests/test_type_api.py` - API integration tests
7. `documentation/sprint_3_documentation.md` - This documentation

### Modified Files

1. `src/api/models/type.py` - Added MultiplierResponse and AllMultipliersResponse models
2. `src/api/routes/type.py` - Added /multiplier and /multipliers endpoints
3. `src/api/routes/__init__.py` - No changes needed (type_router already exported)
4. `src/api/main.py` - No changes needed (type_router already included)

---

## Dependencies

No new dependencies required. Uses existing packages:
- `fastapi` - API framework
- `pydantic` - Response model validation
- `psycopg2-binary` - Database adapter (for seeder only)
- `pytest` - Testing framework

---

## Usage

### Running the Seeder

```bash
# Ensure types table is populated first
python -m src.ingestors.type_effectiveness_seeder
```

### Using the API

**Get single multiplier:**
```bash
curl "http://localhost:8000/types/multiplier?move=fire&defender=grass"
```

**Get dual-type multiplier:**
```bash
curl "http://localhost:8000/types/multiplier?move=fire&defender=grass,steel"
```

**Get all multipliers for coverage analysis:**
```bash
curl "http://localhost:8000/types/multipliers?defender=water,ground"
```

### Using the Service Layer Directly

```python
from src.api.services import calculate_damage_multiplier, all_multipliers_against

# Single multiplier
multiplier = calculate_damage_multiplier("fire", "grass")  # 2.0

# Dual-type multiplier
multiplier = calculate_damage_multiplier("fire", ["grass", "steel"])  # 4.0

# All multipliers (for coverage analysis)
multipliers = all_multipliers_against(["grass", "steel"])
# Returns: {"normal": 0.5, "fire": 4.0, "water": 0.5, ...}
```

---

## Performance Characteristics

| Operation | Time Complexity | Space Complexity |
|-----------|----------------|------------------|
| Initial Matrix Load | O(n) where n=300 rows | O(n) - stores full matrix |
| Single Multiplier Lookup | O(1) | O(1) |
| Dual-Type Calculation | O(1) | O(1) |
| All Multipliers Query | O(t) where t=18 types | O(t) - returns dict |

**Database Queries:**
- Seeder: 2 queries (types + effectiveness)
- Runtime: 0 queries (everything in memory)

---

## Future-Proof Design

This engine is designed to power upcoming sprints:

### Sprint 7-8: Team Weakness Detection
```python
# Example: Find all weaknesses of a team
team_types = [["grass", "steel"], ["water"], ["fire", "flying"]]
weaknesses = analyze_team_weaknesses(team_types)
# Uses all_multipliers_against() under the hood
```

### Sprint 9: Coverage Scoring
```python
# Example: Score team coverage
attacking_types = ["fire", "water", "electric", "grass"]
coverage = calculate_coverage(attacking_types)
# Uses matrix to find types not covered well
```

### Sprint 10: Counter-Team Generation
```python
# Example: Generate counters
target_team = [...]
counters = generate_counters(target_team)
# Uses multipliers to find optimal counters
```

---

## Mental Model

Think of the Type Engine as:

**Linear Algebra over an 18×18 Matrix**

```
Type Effectiveness = Directed Weighted Graph

Edges: (attacker_type) → (defender_type) = multiplier

Matrix M where M[i,j] = multiplier of type i vs type j

Team Analysis = Matrix Operations
  - Weakness detection = column sums
  - Coverage scoring = row analysis
  - Counter generation = inverse operations
```

This matrix-based approach is how advanced competitive systems model type interactions at scale.

---

## Summary

Sprint 3 has successfully implemented:

1. **Type Effectiveness Database**: New `type_effectiveness` table storing the complete 18×18 type matrix

2. **High-Performance Engine**: O(1) in-memory lookups with zero database queries at runtime

3. **Dual-Type Support**: Proper handling of Pokemon with two types via multiplier multiplication

4. **Future-Proof API**: `all_multipliers_against()` function enables coverage analysis and team scoring

5. **Comprehensive Testing**: Both unit tests (synthetic data) and API integration tests with full coverage

6. **Clean Architecture**: Service layer separates business logic from API routes

The system now supports:
- ✅ Pokemon data (from Sprint 1)
- ✅ Abilities and relationships (from Sprint 1)
- ✅ Types (from Sprint 1)
- ✅ Moves and learnsets (from Sprint 2)
- ✅ Type effectiveness calculations (NEW in Sprint 3)

This provides the foundational intelligence layer for:
- Damage calculation in battle simulation
- Team weakness analysis
- Coverage scoring
- AI-powered team building

The Type Effectiveness Engine is ready to power all future battle-related features.
