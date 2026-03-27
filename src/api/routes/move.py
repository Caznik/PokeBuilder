# src/api/routes/move.py
"""Move API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..db import get_db_cursor
from ..models.move import Move, MoveDetail, MoveCategory, MoveList, PokemonMoveEntry

router = APIRouter(prefix="/moves", tags=["moves"])


@router.get("/", response_model=MoveList)
def list_moves(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    type_id: Optional[int] = Query(None, description="Filter by type ID"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    name: Optional[str] = Query(None, description="Filter by name (partial match)")
):
    """Get a paginated list of moves."""
    offset = (page - 1) * page_size
    
    # Build the query
    where_clauses = []
    params = []
    
    if type_id is not None:
        where_clauses.append("type_id = %s")
        params.append(type_id)
    
    if category_id is not None:
        where_clauses.append("category_id = %s")
        params.append(category_id)
    
    if name:
        where_clauses.append("name ILIKE %s")
        params.append(f"%{name}%")
    
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
    
    with get_db_cursor() as cursor:
        # Get total count
        count_sql = f"SELECT COUNT(*) FROM moves {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]
        
        # Get items
        sql = f"""
            SELECT id, name, type_id, power, accuracy, pp, category_id, effect
            FROM moves
            {where_sql}
            ORDER BY id
            LIMIT %s OFFSET %s
        """
        cursor.execute(sql, params + [page_size, offset])
        rows = cursor.fetchall()
        
        items = [
            Move(
                id=row[0],
                name=row[1],
                type_id=row[2],
                power=row[3],
                accuracy=row[4],
                pp=row[5],
                category_id=row[6],
                effect=row[7]
            )
            for row in rows
        ]
    
    return MoveList(
        total=total,
        items=items,
        page=page,
        page_size=page_size
    )


@router.get("/{move_id}", response_model=MoveDetail)
def get_move(move_id: int):
    """Get a specific move by ID with related Pokemon."""
    with get_db_cursor() as cursor:
        # Get move data
        cursor.execute("""
            SELECT m.id, m.name, m.type_id, m.power, m.accuracy, m.pp, m.category_id, m.effect,
                   mc.name as category_name
            FROM moves m
            LEFT JOIN move_categories mc ON m.category_id = mc.id
            WHERE m.id = %s
        """, (move_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Move with id {move_id} not found")
        
        # Get Pokemon that can learn this move
        cursor.execute("""
            SELECT p.id, p.name, pm.learn_method, pm.level
            FROM pokemon_moves pm
            JOIN pokemon p ON pm.pokemon_id = p.id
            WHERE pm.move_id = %s
            ORDER BY p.id
        """, (move_id,))
        
        pokemon = [
            PokemonMoveEntry(
                pokemon_id=pm_row[0],
                pokemon_name=pm_row[1],
                learn_method=pm_row[2],
                level=pm_row[3]
            )
            for pm_row in cursor.fetchall()
        ]
    
    return MoveDetail(
        id=row[0],
        name=row[1],
        type_id=row[2],
        power=row[3],
        accuracy=row[4],
        pp=row[5],
        category_id=row[6],
        effect=row[7],
        category=MoveCategory(id=row[6], name=row[8]) if row[8] else None,
        pokemon=pokemon
    )


@router.get("/name/{name}", response_model=MoveDetail)
def get_move_by_name(name: str):
    """Get a specific move by name."""
    with get_db_cursor() as cursor:
        # Get move data
        cursor.execute("""
            SELECT m.id, m.name, m.type_id, m.power, m.accuracy, m.pp, m.category_id, m.effect,
                   mc.name as category_name
            FROM moves m
            LEFT JOIN move_categories mc ON m.category_id = mc.id
            WHERE m.name ILIKE %s
        """, (name,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Move with name '{name}' not found")
        
        move_id = row[0]
        
        # Get Pokemon that can learn this move
        cursor.execute("""
            SELECT p.id, p.name, pm.learn_method, pm.level
            FROM pokemon_moves pm
            JOIN pokemon p ON pm.pokemon_id = p.id
            WHERE pm.move_id = %s
            ORDER BY p.id
        """, (move_id,))
        
        pokemon = [
            PokemonMoveEntry(
                pokemon_id=pm_row[0],
                pokemon_name=pm_row[1],
                learn_method=pm_row[2],
                level=pm_row[3]
            )
            for pm_row in cursor.fetchall()
        ]
    
    return MoveDetail(
        id=row[0],
        name=row[1],
        type_id=row[2],
        power=row[3],
        accuracy=row[4],
        pp=row[5],
        category_id=row[6],
        effect=row[7],
        category=MoveCategory(id=row[6], name=row[8]) if row[8] else None,
        pokemon=pokemon
    )


@router.get("/categories/", response_model=list[MoveCategory])
def list_move_categories():
    """Get all move categories."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT id, name
            FROM move_categories
            ORDER BY id
        """)
        
        rows = cursor.fetchall()
        
        return [
            MoveCategory(
                id=row[0],
                name=row[1]
            )
            for row in rows
        ]


@router.get("/categories/{category_id}", response_model=MoveCategory)
def get_move_category(category_id: int):
    """Get a specific move category."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT id, name
            FROM move_categories
            WHERE id = %s
        """, (category_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Category with id {category_id} not found")
        
        return MoveCategory(
            id=row[0],
            name=row[1]
        )


@router.get("/pokemon/{pokemon_id}/moves")
def get_pokemon_moves(pokemon_id: int):
    """Get all moves a specific Pokemon can learn."""
    with get_db_cursor() as cursor:
        # First verify the Pokemon exists
        cursor.execute("SELECT id, name FROM pokemon WHERE id = %s", (pokemon_id,))
        pokemon = cursor.fetchone()
        if not pokemon:
            raise HTTPException(status_code=404, detail=f"Pokemon with id {pokemon_id} not found")
        
        # Get moves for this Pokemon
        cursor.execute("""
            SELECT m.id, m.name, m.power, m.accuracy, m.pp, pm.learn_method, pm.level,
                   mc.name as category_name, t.name as type_name
            FROM pokemon_moves pm
            JOIN moves m ON pm.move_id = m.id
            LEFT JOIN move_categories mc ON m.category_id = mc.id
            LEFT JOIN types t ON m.type_id = t.id
            WHERE pm.pokemon_id = %s
            ORDER BY m.name
        """, (pokemon_id,))
        
        rows = cursor.fetchall()
        
        moves = [
            {
                "id": row[0],
                "name": row[1],
                "power": row[2],
                "accuracy": row[3],
                "pp": row[4],
                "learn_method": row[5],
                "level": row[6],
                "category": row[7],
                "type": row[8]
            }
            for row in rows
        ]
        
        return {
            "pokemon_id": pokemon[0],
            "pokemon_name": pokemon[1],
            "moves": moves
        }
