# src/api/routes/type.py
"""Type API routes."""

from fastapi import APIRouter, HTTPException
from ..db import get_db_cursor
from ..models.type import Type, TypeDetail

router = APIRouter(prefix="/types", tags=["types"])


@router.get("/", response_model=list[Type])
def list_types():
    """Get a list of all Pokemon types."""
    with get_db_cursor() as cursor:
        cursor.execute("""
            SELECT id, name
            FROM types
            ORDER BY id
        """)
        
        rows = cursor.fetchall()
        
        return [
            Type(
                id=row[0],
                name=row[1]
            )
            for row in rows
        ]


@router.get("/{type_id}", response_model=TypeDetail)
def get_type(type_id: int):
    """Get a specific type by ID with Pokemon count."""
    with get_db_cursor() as cursor:
        # Get type data
        cursor.execute("""
            SELECT id, name
            FROM types
            WHERE id = %s
        """, (type_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Type with id {type_id} not found")
        
        # Count Pokemon with this type
        cursor.execute("""
            SELECT COUNT(DISTINCT pokemon_id)
            FROM pokemon_types
            WHERE type_id = %s
        """, (type_id,))
        
        pokemon_count = cursor.fetchone()[0]
    
    return TypeDetail(
        id=row[0],
        name=row[1],
        pokemon_count=pokemon_count
    )


@router.get("/name/{name}", response_model=TypeDetail)
def get_type_by_name(name: str):
    """Get a specific type by name."""
    with get_db_cursor() as cursor:
        # Get type data
        cursor.execute("""
            SELECT id, name
            FROM types
            WHERE name ILIKE %s
        """, (name,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Type with name '{name}' not found")
        
        type_id = row[0]
        
        # Count Pokemon with this type
        cursor.execute("""
            SELECT COUNT(DISTINCT pokemon_id)
            FROM pokemon_types
            WHERE type_id = %s
        """, (type_id,))
        
        pokemon_count = cursor.fetchone()[0]
    
    return TypeDetail(
        id=row[0],
        name=row[1],
        pokemon_count=pokemon_count
    )


@router.get("/{type_id}/pokemon")
def get_pokemon_by_type(type_id: int):
    """Get all Pokemon of a specific type."""
    with get_db_cursor() as cursor:
        # First verify the type exists
        cursor.execute("SELECT id, name FROM types WHERE id = %s", (type_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"Type with id {type_id} not found")
        
        # Get Pokemon with this type
        cursor.execute("""
            SELECT p.id, p.name, p.generation,
                   p.base_hp, p.base_attack, p.base_defense,
                   p.base_sp_attack, p.base_sp_defense, p.base_speed
            FROM pokemon p
            JOIN pokemon_types pt ON p.id = pt.pokemon_id
            WHERE pt.type_id = %s
            ORDER BY p.id
        """, (type_id,))
        
        rows = cursor.fetchall()
        
        return [
            {
                "id": row[0],
                "name": row[1],
                "generation": row[2],
                "base_hp": row[3],
                "base_attack": row[4],
                "base_defense": row[5],
                "base_sp_attack": row[6],
                "base_sp_defense": row[7],
                "base_speed": row[8]
            }
            for row in rows
        ]
