# src/api/routes/pokemon.py
"""Pokemon API routes."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..db import get_db_cursor
from ..models.pokemon import PokemonWithTypes, PokemonDetail, PokemonList, PokemonAbility, PokemonType

router = APIRouter(prefix="/pokemon", tags=["pokemon"])


@router.get("/", response_model=PokemonList)
def list_pokemon(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    generation: Optional[int] = Query(None, description="Filter by generation"),
    name: Optional[str] = Query(None, description="Filter by name (partial match)"),
    type_name: Optional[str] = Query(None, alias="type", description="Filter by type name"),
):
    """Get a paginated list of Pokemon with their types."""
    offset = (page - 1) * page_size

    where_clauses = []
    params = []

    if generation is not None:
        where_clauses.append("generation = %s")
        params.append(generation)

    if name:
        where_clauses.append("name ILIKE %s")
        params.append(f"%{name}%")

    if type_name:
        where_clauses.append(
            "id IN (SELECT pt.pokemon_id FROM pokemon_types pt "
            "JOIN types t ON t.id = pt.type_id WHERE t.name ILIKE %s)"
        )
        params.append(type_name)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    with get_db_cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM pokemon {where_sql}", params)
        total = cursor.fetchone()[0]

        cursor.execute(
            f"""
            SELECT id, name, generation,
                   base_hp, base_attack, base_defense,
                   base_sp_attack, base_sp_defense, base_speed
            FROM pokemon
            {where_sql}
            ORDER BY id
            LIMIT %s OFFSET %s
            """,
            params + [page_size, offset],
        )
        rows = cursor.fetchall()

        types_map: dict = {}
        if rows:
            pokemon_ids = [row[0] for row in rows]
            cursor.execute(
                """
                SELECT pt.pokemon_id, t.id, t.name
                FROM pokemon_types pt
                JOIN types t ON pt.type_id = t.id
                WHERE pt.pokemon_id = ANY(%s)
                """,
                (pokemon_ids,),
            )
            for tr in cursor.fetchall():
                types_map.setdefault(tr[0], []).append(
                    PokemonType(type_id=tr[1], type_name=tr[2])
                )

        items = [
            PokemonWithTypes(
                id=row[0], name=row[1], generation=row[2],
                base_hp=row[3], base_attack=row[4], base_defense=row[5],
                base_sp_attack=row[6], base_sp_defense=row[7], base_speed=row[8],
                types=types_map.get(row[0], []),
            )
            for row in rows
        ]

    return PokemonList(total=total, items=items, page=page, page_size=page_size)


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
