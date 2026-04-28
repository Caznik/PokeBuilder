# src/api/models/generation.py
"""Pydantic models for the team generation endpoint."""

from pydantic import BaseModel

from .team import CoverageResult


class GenerationConstraints(BaseModel):
    include: list[str] = []
    exclude: list[str] = []


class GenerateRequest(BaseModel):
    constraints: GenerationConstraints | None = None


class GenerationMember(BaseModel):
    pokemon_name: str
    set_id: int
    set_name: str | None = None


class TeamAnalysis(BaseModel):
    valid: bool
    issues: list[str]
    roles: dict[str, int]
    weaknesses: dict[str, int]
    resistances: dict[str, int]
    coverage: CoverageResult


class TeamResult(BaseModel):
    score: float
    members: list[GenerationMember]
    analysis: TeamAnalysis


class GenerationResponse(BaseModel):
    teams: list[TeamResult]
    generated: int
    valid_found: int
