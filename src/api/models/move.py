# src/api/models/move.py
"""Pydantic models for Move data."""

from pydantic import BaseModel
from typing import Optional, List


class MoveCategory(BaseModel):
    """Move category model (physical/special/status)."""
    id: int
    name: str
    
    class Config:
        from_attributes = True


class Move(BaseModel):
    """Move model."""
    id: int
    name: str
    type_id: int
    power: Optional[int] = None
    accuracy: Optional[int] = None
    pp: Optional[int] = None
    category_id: int
    effect: Optional[str] = None
    
    class Config:
        from_attributes = True


class PokemonMoveEntry(BaseModel):
    """Pokemon that can learn this move."""
    pokemon_id: int
    pokemon_name: str
    learn_method: str
    level: Optional[int] = None


class MoveDetail(Move):
    """Move model with related Pokemon."""
    category: Optional[MoveCategory] = None
    pokemon: List[PokemonMoveEntry] = []


class MoveList(BaseModel):
    """Paginated list of moves."""
    total: int
    items: List[Move]
    page: int
    page_size: int
