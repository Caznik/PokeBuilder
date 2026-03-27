# PokeBuilder Documentation

Welcome to the PokeBuilder project documentation. This file serves as the central hub for all project documentation, organized by sprints.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Sprint Documentation](#sprint-documentation)
   - [Sprint 1: Data Ingestion & API Foundation](#sprint-1-data-ingestion--api-foundation)
   - [Next Sprint: TBD](#next-sprint-tbd)
3. [Getting Started](#getting-started)
4. [Architecture Overview](#architecture-overview)

---

## Project Overview

PokeBuilder is a Pokemon team building and analysis application. It ingests data from the PokeAPI and provides a REST API for querying Pokemon information, abilities, types, and statistics.

### Key Features

- **Data Ingestion**: Automated fetchers for Pokemon, abilities, types, and moves
- **REST API**: FastAPI-based API for querying ingested data
- **PostgreSQL Database**: Normalized schema for efficient data storage
- **Docker Support**: Containerized deployment for easy setup

---

## Sprint Documentation

### Sprint 1: Data Ingestion & API Foundation

**Status**: ✅ Completed  
**Duration**: Sprint 1  
**Goal**: Establish data pipeline and basic REST API

#### Summary

Sprint 1 focused on creating the foundational infrastructure for the PokeBuilder application. We successfully implemented:

1. **Data Fetchers**: Three Python scripts that extract data from the PokeAPI and store it in a PostgreSQL database:
   - `pokemon_fetcher.py`: Fetches all Pokemon with their base stats and generation
   - `pokemon_abilities_fetcher.py`: Fetches abilities and Pokemon-ability relationships
   - `pokemon_types_fetcher.py`: Fetches Pokemon types

2. **Database Schema**: A normalized PostgreSQL schema with five tables:
   - `pokemon`: Core Pokemon data with base stats
   - `abilities`: Pokemon abilities with descriptions
   - `types`: Pokemon types
   - `pokemon_abilities`: Many-to-many junction table
   - `pokemon_types`: Many-to-many junction table with slot ordering

3. **REST API**: A complete FastAPI application with:
   - Endpoints for Pokemon, abilities, and types
   - Pagination, filtering, and search capabilities
   - Parameterized queries for SQL injection prevention
   - Pydantic models for request/response validation
   - Interactive API documentation (Swagger UI)

4. **Infrastructure**: Docker and Docker Compose configuration for easy deployment

#### Technical Highlights

- **Framework**: FastAPI with Pydantic for data validation
- **Database**: PostgreSQL 16 with psycopg2
- **Security**: Parameterized queries prevent SQL injection
- **Performance**: Connection pooling and parallel data fetching
- **Documentation**: Auto-generated OpenAPI/Swagger documentation

#### Deliverables

- ✅ Three data fetcher scripts (`src/ingestors/`)
- ✅ Database schema definitions (`resources/sql/tables_schemas/`)
- ✅ REST API with full CRUD operations (`src/api/`)
- ✅ Docker configuration (`Dockerfile`, `docker-compose.yml`)
- ✅ Complete API documentation at `/docs` endpoint

#### Files Created

```
src/
├── ingestors/
│   ├── pokemon_fetcher.py
│   ├── pokemon_abilities_fetcher.py
│   └── pokemon_types_fetcher.py
└── api/
    ├── main.py
    ├── db.py
    ├── models/
    │   ├── pokemon.py
    │   ├── ability.py
    │   └── type.py
    └── routes/
        ├── pokemon.py
        ├── ability.py
        └── type.py

documentation/
├── documentation.md
└── sprint_1_documentation.md

Dockerfile
docker-compose.yml
```

#### Detailed Documentation

For comprehensive details on Sprint 1, see: [Sprint 1 Documentation](./sprint_1_documentation.md)

---

### Sprint 2: Pokemon Moves

**Status**: ✅ Completed  
**Duration**: Sprint 2  
**Goal**: Add comprehensive Pokemon moves data and API endpoints

#### Summary

Sprint 2 focused on implementing Pokemon moves functionality, building upon the foundation established in Sprint 1. We successfully implemented:

1. **Move Data Fetcher**: `pokemon_moves_fetcher.py`
   - Fetches all moves from PokeAPI with detailed stats (power, accuracy, PP, type, category)
   - Extracts move effects and descriptions
   - Establishes Pokemon-move relationships with learn methods and levels
   - Parallel fetching for optimal performance

2. **Enhanced Database Schema**: Three new tables
   - `moves`: Complete move data including power, accuracy, PP, type, category, and effects
   - `move_categories`: Pre-populated with physical/special/status categories
   - `pokemon_moves`: Many-to-many junction table tracking learn methods and levels

3. **Extended REST API**: New endpoints for moves
   - `/moves/` - List and filter moves by type, category, or name
   - `/moves/{move_id}` - Get detailed move information with Pokemon that can learn it
   - `/moves/categories/` - List move categories (physical/special/status)
   - `/moves/pokemon/{pokemon_id}/moves` - Get all moves a Pokemon can learn

4. **Bug Fixes**: Fixed column naming inconsistency in moves.sql schema

#### Technical Highlights

- **Move Categories**: Mapped PokeAPI's damage_class to our category system (physical/special/status)
- **Learn Methods**: Comprehensive tracking of how Pokemon learn moves (level-up, TM, tutor, etc.)
- **Effect Text**: English move descriptions extracted and stored
- **Query Safety**: All queries use parameterized statements for SQL injection prevention

#### Deliverables

- ✅ Move data fetcher script (`src/ingestors/pokemon_moves_fetcher.py`)
- ✅ Move database tables and schemas (`moves`, `move_categories`, `pokemon_moves`)
- ✅ Move API endpoints with filtering and pagination
- ✅ Move Pydantic models for request/response validation
- ✅ Fixed schema typo (category → category_id)

#### Files Created/Modified

```
src/
├── ingestors/
│   └── pokemon_moves_fetcher.py          # NEW
└── api/
    ├── main.py                           # MODIFIED
    ├── models/
    │   ├── __init__.py                   # MODIFIED
    │   └── move.py                       # NEW
    └── routes/
        ├── __init__.py                   # MODIFIED
        └── move.py                       # NEW

resources/sql/tables_schemas/
└── moves.sql                             # MODIFIED (bugfix)

documentation/
└── sprint_2_documentation.md             # NEW
```

#### Detailed Documentation

For comprehensive details on Sprint 2, see: [Sprint 2 Documentation](./sprint_2_documentation.md)

---

### Next Sprint: TBD

**Status**: 🔄 Planned  
**Goal**: [To be determined based on project priorities]

#### Potential Features

Based on the current foundation, the next sprint could focus on:

1. **Team Building API**
   - Create team management endpoints (CRUD operations)
   - Team validation (type coverage, stat balancing)
   - Team persistence and retrieval

2. **Battle Simulation**
   - Type effectiveness calculations
   - Stat comparison algorithms
   - Battle outcome prediction
   - Move selection strategies

3. **Advanced Search & Filtering**
   - Complex queries (e.g., "fire type Pokemon with high attack")
   - Stat range filtering
   - Multi-criteria search
   - Move-based filtering (e.g., "Pokemon that can learn Surf")

4. **Data Enhancement**
   - Additional PokeAPI endpoints (items, evolutions, etc.)
   - Caching layer for frequently accessed data
   - Data synchronization/updates

5. **Authentication & User Management**
   - User accounts and authentication
   - Personal team collections
   - Sharing capabilities

6. **Performance Optimization**
   - Database indexing strategies
   - Query optimization
   - Response caching

#### Documentation Structure

As the project grows, this section will be expanded to include:
- Sprint goals and objectives
- Technical design decisions
- Implementation details
- Testing strategies
- Deployment notes

---

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ (or Docker)
- Docker & Docker Compose (optional)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd PokeBuilder
   ```

2. **Set up environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Start PostgreSQL**
   ```bash
   docker compose up postgres -d
   ```

4. **Run data fetchers**
   ```bash
   python src/ingestors/pokemon_fetcher.py
   python src/ingestors/pokemon_abilities_fetcher.py
   python src/ingestors/pokemon_types_fetcher.py
   python src/ingestors/pokemon_moves_fetcher.py
   ```

5. **Start the API**
   ```bash
   uvicorn src.api.main:app --reload
   ```

6. **Access the API**
   - API Base URL: http://localhost:8000
   - Documentation: http://localhost:8000/docs

### Docker Deployment

Run everything with Docker Compose:

```bash
docker compose up -d
```

This will start:
- PostgreSQL database on port 5432
- FastAPI application on port 8000

---

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│                 Client Applications           │
│         (Web, Mobile, CLI, etc.)            │
└──────────────────────┬──────────────────────┘
                       │ HTTP/JSON
                       ▼
┌─────────────────────────────────────────────┐
│                  FastAPI                      │
│              (REST Endpoints)                 │
│                                               │
│  ┌──────────┬──────────┬──────────┬──────────┐│
│  │ Pokemon  │ Abilities│   Types  │   Moves  ││
│  │  Routes  │  Routes  │  Routes  │  Routes  ││
│  └────┬─────┴────┬─────┴────┬────┴────┬───┘│
│       └──────────┴──────────┘          │     │
│                  ▼                       │     │
│           Database Layer                 │     │
│         (psycopg2 + Connection Pool)   │     │
└──────────────────┬─────────────────────┘     │
                   │ SQL
                   ▼
┌─────────────────────────────────────────────┐
│              PostgreSQL Database              │
│                                               │
│  ┌─────────┬──────────┬──────────┬────────┐ │
│  │ pokemon │ abilities│   types  │ moves  │ │
│  └────┬────┴─────┬────┴─────┬────┴───┬────┘ │
│       │          │          │        │       │
│  ┌────┴──────────┴─────┐ ┌┴─────────┴────┐ │
│  │  pokemon_abilities   │ │pokemon_types  │ │
│  └──────────────────────┘ │pokemon_moves   │ │
│                           └────────────────┘ │
└─────────────────────────────────────────────┘
                   ▲
                   │ Data
                   │ Fetching
                   │
┌─────────────────────────────────────────────┐
│                PokeAPI                        │
│         (https://pokeapi.co/)                 │
└─────────────────────────────────────────────┘
```

### Component Responsibilities

- **PokeAPI**: External data source for Pokemon information
- **Data Fetchers**: Scripts that ingest data from PokeAPI to PostgreSQL
- **PostgreSQL**: Persistent storage with normalized schema
- **FastAPI**: RESTful API layer with business logic
- **Client Applications**: Consumers of the API (to be built in future sprints)

---

## Contributing

When adding new features:

1. Update this documentation file with sprint information
2. Create detailed sprint documentation in `sprint_X_documentation.md`
3. Follow existing code patterns and conventions
4. Ensure SQL queries use parameterized statements
5. Add appropriate error handling and validation
6. Update API documentation (FastAPI handles this automatically)

---

## License

[License information to be added]

---

## Contact

[Project maintainer contact information]

---

*Last updated: March 26, 2026*
