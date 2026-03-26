# src/api/routes/pokemon.py
"""Pokemon API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..db import get_db_cursor
from ..models.pokemon import Pokemon, PokemonDetail, PokemonList, PokemonAbility, PokemonType

router = APIRouter(prefix="/pokemon", tags=["pokemon"])


@router.get("/", response_model=PokemonList)
def list_pokemon(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    generation: Optional[int] = Query(None, description="Filter by generation"),
    name: Optional[str] = Query(None, description="Filter by name (partial match)")
):
    """Get a paginated list of Pokemon."""
    offset = (page - 1) * page_size
    
    # Build the query
    where_clauses = []
    params = []
    
    if generation is not None:
        where_clauses.append("generation = %s")
        params.append(generation)
    
    if name:
        where_clauses.append("name ILIKE %s")
        params.append(f"%{name}%")
    
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
    
    with get_db_cursor() as cursor:
        # Get total count
        count_sql = f"SELECT COUNT(*) FROM pokemon {where_sql}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()[0]
        
        # Get items
        sql = f"""
            SELECT id, name, generation,
                   base_hp, base_attack, base_defense,
                   base_sp_attack, base_sp_defense, base_speed
            FROM pokemon
            {where_sql}
            ORDER BY id
            LIMIT %s OFFSET %s
        """
        cursor.execute(sql, params + [page_size, offset])
        rows = cursor.fetchall()
        
        items = [
            Pokemon(
                id=row[0],
                name=row[1],
                generation=row[2],
                base_hp=row[3],
                base_attack=row[4],
                base_defense=row[5],
                base_sp_attack=row[6],
                base_sp_defense=row[7],
                base_speed=row[8]
            )
            for row in rows
        ]
    
    return PokemonList(
        total=total,
        items=items,
        page=page,
        page_size=page_size
    )


@router.get("/{pokemon_id}", response_model=PokemonDetail)
def get_pokemon(pokemon_id: int):
    """Get a specific Pokemon by ID with its abilities."""
    with get_db_cursor() as cursor:
        # Get Pokemon base data
        cursor.execute("""
            SELECT id, name, generation,
                   base_hp, base_attack, base_defense,
                   base_sp_attack, base_sp_defense, base_speed
            FROM pokemon
            WHERE id = %s
        """, (pokemon_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Pokemon with id {pokemon_id} not found")
        
        # Get abilities
        cursor.execute("""
            SELECT a.id, a.name, pa.is_hidden
            FROM pokemon_abilities pa
            JOIN abilities a ON pa.ability_id = a.id
            WHERE pa.pokemon_id = %s
        """, (pokemon_id,))
        
        abilities = [
            PokemonAbility(
                ability_id=abil_row[0],
                ability_name=abil_row[1],
                is_hidden=abil_row[2]
            )
            for abil_row in cursor.fetchall()
        ]
        
        # Get types
        cursor.execute("""
            SELECT t.id, t.name
            FROM pokemon_types pt
            JOIN types t ON pt.type_id = t.id
            WHERE pt.pokemon_id = %s
        """, (pokemon_id,))
        
        types = [
            PokemonType(
                type_id=type_row[0],
                type_name=type_row[1]
            )
            for type_row in cursor.fetchall()
        ]
    
    return PokemonDetail(
        id=row[0],
        name=row[1],
        generation=row[2],
        base_hp=row[3],
        base_attack=row[4],
        base_defense=row[5],
        base_sp_attack=row[6],
        base_sp_defense=row[7],
        base_speed=row[8],
        abilities=abilities,
        types=types
    )


@router.get("/name/{name}", response_model=PokemonDetail)
def get_pokemon_by_name(name: str):
    """Get a specific Pokemon by name."""
    with get_db_cursor() as cursor:
        # Get Pokemon base data
        cursor.execute("""
            SELECT id, name, generation,
                   base_hp, base_attack, base_defense,
                   base_sp_attack, base_sp_defense, base_speed
            FROM pokemon
            WHERE name ILIKE %s
        """, (name,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Pokemon with name '{name}' not found")
        
        pokemon_id = row[0]
        
        # Get abilities
        cursor.execute("""
            SELECT a.id, a.name, pa.is_hidden
            FROM pokemon_abilities pa
            JOIN abilities a ON pa.ability_id = a.id
            WHERE pa.pokemon_id = %s
        """, (pokemon_id,))
        
        abilities = [
            PokemonAbility(
                ability_id=abil_row[0],
                ability_name=abil_row[1],
                is_hidden=abil_row[2]
            )
            for abil_row in cursor.fetchall()
        ]
        
        # Get types
        cursor.execute("""
            SELECT t.id, t.name
            FROM pokemon_types pt
            JOIN types t ON pt.type_id = t.id
            WHERE pt.pokemon_id = %s
        """, (pokemon_id,))
        
        types = [
            PokemonType(
                type_id=type_row[0],
                type_name=type_row[1]
            )
            for type_row in cursor.fetchall()
        ]
    
    return PokemonDetail(
        id=row[0],
        name=row[1],
        generation=row[2],
        base_hp=row[3],
        base_attack=row[4],
        base_defense=row[5],
        base_sp_attack=row[6],
        base_sp_defense=row[7],
        base_speed=row[8],
        abilities=abilities,
        types=types
    )
