# src/api/models/pokemon.py
"""Pydantic models for Pokemon data."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class PokemonBase(BaseModel):
    """Base Pokemon model with core fields."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    generation: Optional[int] = None


class PokemonStats(BaseModel):
    """Pokemon stats model."""
    base_hp: int
    base_attack: int
    base_defense: int
    base_sp_attack: int
    base_sp_defense: int
    base_speed: int


class Pokemon(PokemonBase, PokemonStats):
    """Complete Pokemon model."""
    pass


class PokemonAbility(BaseModel):
    """Pokemon ability relationship model."""
    ability_id: int
    ability_name: str
    is_hidden: bool


class PokemonType(BaseModel):
    """Pokemon type relationship model."""
    type_id: int
    type_name: str


class PokemonDetail(Pokemon):
    """Pokemon model with relationships."""
    abilities: List[PokemonAbility] = []
    types: List[PokemonType] = []


class PokemonList(BaseModel):
    """Paginated list of Pokemon."""
    total: int
    items: List[Pokemon]
    page: int
    page_size: int
