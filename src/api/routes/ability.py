# src/api/routes/ability.py
"""Ability API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..db import get_db_cursor
from ..models.ability import Ability, AbilityDetail, AbilityPokemon

router = APIRouter(prefix="/abilities", tags=["abilities"])


@router.get("/", response_model=list[Ability])
def list_abilities(
    name: Optional[str] = Query(None, description="Filter by name (partial match)")
):
    """Get a list of all abilities."""
    with get_db_cursor() as cursor:
        if name:
            cursor.execute("""
                SELECT id, name, description
                FROM abilities
                WHERE name ILIKE %s
                ORDER BY id
            """, (f"%{name}%",))
        else:
            cursor.execute("""
                SELECT id, name, description
                FROM abilities
                ORDER BY id
            """)
        
        rows = cursor.fetchall()
        
        return [
            Ability(
                id=row[0],
                name=row[1],
                description=row[2]
            )
            for row in rows
        ]


@router.get("/{ability_id}", response_model=AbilityDetail)
def get_ability(ability_id: int):
    """Get a specific ability by ID with related Pokemon."""
    with get_db_cursor() as cursor:
        # Get ability data
        cursor.execute("""
            SELECT id, name, description
            FROM abilities
            WHERE id = %s
        """, (ability_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Ability with id {ability_id} not found")
        
        # Get Pokemon that have this ability
        cursor.execute("""
            SELECT p.id, p.name, pa.is_hidden
            FROM pokemon_abilities pa
            JOIN pokemon p ON pa.pokemon_id = p.id
            WHERE pa.ability_id = %s
            ORDER BY p.id
        """, (ability_id,))
        
        pokemon = [
            AbilityPokemon(
                pokemon_id=poke_row[0],
                pokemon_name=poke_row[1],
                is_hidden=poke_row[2]
            )
            for poke_row in cursor.fetchall()
        ]
    
    return AbilityDetail(
        id=row[0],
        name=row[1],
        description=row[2],
        pokemon=pokemon
    )


@router.get("/name/{name}", response_model=AbilityDetail)
def get_ability_by_name(name: str):
    """Get a specific ability by name."""
    with get_db_cursor() as cursor:
        # Get ability data
        cursor.execute("""
            SELECT id, name, description
            FROM abilities
            WHERE name ILIKE %s
        """, (name,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Ability with name '{name}' not found")
        
        ability_id = row[0]
        
        # Get Pokemon that have this ability
        cursor.execute("""
            SELECT p.id, p.name, pa.is_hidden
            FROM pokemon_abilities pa
            JOIN pokemon p ON pa.pokemon_id = p.id
            WHERE pa.ability_id = %s
            ORDER BY p.id
        """, (ability_id,))
        
        pokemon = [
            AbilityPokemon(
                pokemon_id=poke_row[0],
                pokemon_name=poke_row[1],
                is_hidden=poke_row[2]
            )
            for poke_row in cursor.fetchall()
        ]
    
    return AbilityDetail(
        id=row[0],
        name=row[1],
        description=row[2],
        pokemon=pokemon
    )
