# src/api/models/type.py
"""Pydantic models for Type data."""

from pydantic import BaseModel
from typing import List


class Type(BaseModel):
    """Type model."""
    id: int
    name: str
    
    class Config:
        from_attributes = True


class TypeDetail(Type):
    """Type model with relationships."""
    pokemon_count: int = 0
