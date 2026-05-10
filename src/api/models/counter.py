# src/api/models/counter.py
"""Pydantic models for the counter team endpoint."""

from pydantic import BaseModel, Field

from .generation import TeamResult


class CounterRequest(BaseModel):
    regulation_id: int
    beam_width: int = Field(default=20, ge=1, le=50)
    meta_top_n: int = Field(default=10, ge=1, le=30)


class MetaPokemon(BaseModel):
    name: str
    usage_pct: float


class MetaSnapshot(BaseModel):
    top_pokemon: list[MetaPokemon]
    total_battles: int


class CounterResponse(BaseModel):
    best_teams: list[TeamResult]
    algorithm: str
    meta_snapshot: MetaSnapshot
    replays_analyzed: int
