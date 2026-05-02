# src/api/models/optimization.py
"""Pydantic models for the team optimization endpoint."""

from pydantic import BaseModel, Field, field_validator

from .generation import GenerationConstraints, TeamResult


class OptimizeRequest(BaseModel):
    constraints: GenerationConstraints | None = None
    population_size: int = Field(default=50, ge=1)
    generations: int = Field(default=30, ge=1)

    @field_validator("population_size")
    @classmethod
    def cap_population_size(cls, v: int) -> int:
        return min(v, 100)

    @field_validator("generations")
    @classmethod
    def cap_generations(cls, v: int) -> int:
        return min(v, 50)


class OptimizationResponse(BaseModel):
    best_teams: list[TeamResult]
    generations_run: int
    initial_population: int
    evaluations: int
