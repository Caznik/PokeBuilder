# src/api/models/regulation.py
"""Pydantic models for VGC regulations."""

from pydantic import BaseModel


class RegulationCreate(BaseModel):
    """Request schema for creating a new regulation."""

    name: str
    description: str | None = None
    pokemon_names: list[str]


class RegulationUpdate(BaseModel):
    """Request schema for partially updating a regulation (PATCH)."""

    name: str | None = None
    description: str | None = None
    pokemon_names: list[str] | None = None


class RegulationResponse(BaseModel):
    """Response schema for regulation list endpoints."""

    id: int
    name: str
    description: str | None = None


class RegulationDetail(RegulationResponse):
    """Response schema for regulation detail endpoints, including the full Pokémon allowlist."""

    pokemon: list[str]
