# src/api/models/ability.py
"""Pydantic models for Ability data."""

from pydantic import BaseModel
from typing import Optional, List


class Ability(BaseModel):
    """Ability model."""
    id: int
    name: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class AbilityPokemon(BaseModel):
    """Pokemon that has this ability."""
    pokemon_id: int
    pokemon_name: str
    is_hidden: bool


class AbilityDetail(Ability):
    """Ability model with related Pokemon."""
    pokemon: List[AbilityPokemon] = []
