# src/api/models/ability.py
"""Pydantic models for Ability data."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class Ability(BaseModel):
    """Ability model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str] = None


class AbilityPokemon(BaseModel):
    """Pokemon that has this ability."""
    pokemon_id: int
    pokemon_name: str
    is_hidden: bool


class AbilityDetail(Ability):
    """Ability model with related Pokemon."""
    pokemon: List[AbilityPokemon] = []
