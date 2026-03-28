# src/api/models/type.py
"""Pydantic models for Type data."""

from pydantic import BaseModel, ConfigDict
from typing import Dict, List


class Type(BaseModel):
    """Type model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str


class TypeDetail(Type):
    """Type model with relationships."""
    pokemon_count: int = 0


class MultiplierResponse(BaseModel):
    """Response model for single multiplier query."""
    multiplier: float


class AllMultipliersResponse(BaseModel):
    """Response model for all multipliers against a defender."""
    multipliers: Dict[str, float]


class TypeList(BaseModel):
    """List of all types."""
    items: List[Type]
