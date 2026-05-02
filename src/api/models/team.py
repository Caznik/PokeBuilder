# src/api/models/team.py
"""Pydantic models for team analysis API."""

from dataclasses import dataclass, field
from typing import Optional
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Internal domain objects (dataclasses — not exposed via API)
# ---------------------------------------------------------------------------

@dataclass
class MoveDetail:
    name: str
    type: str
    category: str  # "physical" | "special" | "status"


@dataclass
class PokemonBuild:
    pokemon_name: str
    set_id: int
    types: list[str]
    nature: Optional[str]
    ability: Optional[str]
    item: Optional[str]
    stats: dict[str, int]   # hp, attack, defense, sp_attack, sp_defense, speed
    moves: list[MoveDetail] = field(default_factory=list)
    evs: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# API input models
# ---------------------------------------------------------------------------

class TeamMemberInput(BaseModel):
    pokemon_name: str
    set_id: int


class TeamInput(BaseModel):
    team: list[TeamMemberInput]

    @field_validator("team")
    @classmethod
    def must_have_six_members(cls, v):
        if len(v) != 6:
            raise ValueError(f"Team must have exactly 6 members, got {len(v)}")
        return v


# ---------------------------------------------------------------------------
# API response models
# ---------------------------------------------------------------------------

class CoverageResult(BaseModel):
    covered_types: list[str]
    missing_types: list[str]


class TeamAnalysisResponse(BaseModel):
    valid: bool
    issues: list[str]
    roles: dict[str, int]
    weaknesses: dict[str, int]
    resistances: dict[str, int]
    coverage: CoverageResult
    speed_control_archetype: str = "none"
