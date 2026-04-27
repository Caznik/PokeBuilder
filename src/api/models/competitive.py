# src/api/models/competitive.py
"""Pydantic models for competitive sets."""

from typing import Optional
from pydantic import BaseModel


class CompetitiveSetEvs(BaseModel):
    hp: int = 0
    attack: int = 0
    defense: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    speed: int = 0


class CompetitiveSet(BaseModel):
    id: int
    name: Optional[str]
    nature: Optional[str]
    ability: Optional[str]
    item: Optional[str]
    evs: CompetitiveSetEvs
    moves: list[str]


class CompetitiveSetResponse(BaseModel):
    pokemon: str
    sets: list[CompetitiveSet]
