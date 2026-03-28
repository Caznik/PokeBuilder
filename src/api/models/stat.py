# src/api/models/stat.py
"""Pydantic models for stat calculation."""

from typing import Dict, Literal
from pydantic import BaseModel, Field, field_validator


StatKey = Literal["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]


class StatInput(BaseModel):
    """Payload for stat calculation."""
    pokemon: str  # name matching the `pokemon` table
    level: int = Field(100, ge=1, le=100)  # 1-100 inclusive
    nature: str = "hardy"  # default neutral nature
    evs: Dict[StatKey, int] = Field(default_factory=dict)  # omitted stats default to 0
    ivs: Dict[StatKey, int] = Field(default_factory=dict)  # omitted stats default to 31

    @field_validator("evs", mode="before")
    @classmethod
    def _default_evs(cls, v):
        if v is None:
            return {}
        return v

    @field_validator("ivs", mode="before")
    @classmethod
    def _default_ivs(cls, v):
        if v is None:
            return {}
        return v

    @field_validator("evs")
    @classmethod
    def _validate_evs(cls, v: Dict[StatKey, int]) -> Dict[StatKey, int]:
        total = sum(v.values())
        if total > 510:
            raise ValueError("Total EVs may not exceed 510")
        for stat, val in v.items():
            if not 0 <= val <= 252:
                raise ValueError(f"EV for {stat} must be between 0 and 252")
        return v

    @field_validator("ivs")
    @classmethod
    def _validate_ivs(cls, v: Dict[StatKey, int]) -> Dict[StatKey, int]:
        for stat, val in v.items():
            if not 0 <= val <= 31:
                raise ValueError(f"IV for {stat} must be between 0 and 31")
        return v


class StatOutput(BaseModel):
    """Returned final stats."""
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int
