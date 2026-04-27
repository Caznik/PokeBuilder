# src/api/routes/competitive.py
"""Competitive sets API routes."""

from fastapi import APIRouter, HTTPException
from ..models.competitive import CompetitiveSetResponse, CompetitiveSet, CompetitiveSetEvs
from ..services.competitive_service import get_sets_for_pokemon
from ..db import get_db_cursor

router = APIRouter(prefix="/competitive-sets", tags=["competitive-sets"])


@router.get("/{pokemon_name}", response_model=CompetitiveSetResponse)
def get_competitive_sets(pokemon_name: str):
    """Get all stored competitive sets for a Pokémon.

    Returns an empty sets list when the Pokémon exists but has no ingested sets yet.

    Args:
        pokemon_name: Pokémon name (case-insensitive).
    """
    try:
        with get_db_cursor() as cursor:
            raw_sets = get_sets_for_pokemon(cursor, pokemon_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    sets = [
        CompetitiveSet(
            id=s["id"],
            name=s["name"],
            nature=s["nature"],
            ability=s["ability"],
            item=s["item"],
            evs=CompetitiveSetEvs(**s["evs"]),
            moves=s["moves"],
        )
        for s in raw_sets
    ]

    return CompetitiveSetResponse(pokemon=pokemon_name.lower(), sets=sets)
