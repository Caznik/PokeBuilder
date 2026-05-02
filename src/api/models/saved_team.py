# src/api/models/saved_team.py
"""Pydantic models for the saved teams API."""

from datetime import datetime
from pydantic import BaseModel, field_validator

from .team import TeamMemberInput, TeamAnalysisResponse
from .scoring import ScoreBreakdown


class SaveTeamRequest(BaseModel):
    """Request to save a team with its score snapshot.

    score, breakdown, and analysis are forwarded from a prior /team/generate
    or /team/optimize response — they are not user-fabricated values.
    """
    name: str
    members: list[TeamMemberInput]
    score: float
    breakdown: ScoreBreakdown
    analysis: TeamAnalysisResponse

    @field_validator("members")
    @classmethod
    def must_have_six(cls, v: list) -> list:
        if len(v) != 6:
            raise ValueError(f"Team must have exactly 6 members, got {len(v)}")
        return v

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v


class UpdateTeamRequest(BaseModel):
    name: str | None = None
    score: float | None = None
    breakdown: ScoreBreakdown | None = None
    analysis: TeamAnalysisResponse | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("name cannot be empty")
        return v

    def has_update(self) -> bool:
        return any(f is not None for f in [self.name, self.score, self.breakdown, self.analysis])


class UpdateMemberRequest(BaseModel):
    pokemon_name: str
    set_id: int
    item: str | None = None
    tera_type: str | None = None
    evs: dict | None = None
    moves: list[str] | None = None
    nature: str | None = None
    ability: str | None = None


class SavedTeamMember(BaseModel):
    slot: int
    pokemon_name: str
    set_id: int
    set_name: str | None = None
    nature: str | None = None
    ability: str | None = None
    item: str | None = None
    tera_type: str | None = None
    evs: dict | None = None
    moves: list[str] | None = None


class SavedTeamSummary(BaseModel):
    id: int
    name: str
    score: float
    created_at: datetime
    members: list[SavedTeamMember]


class SavedTeamDetail(SavedTeamSummary):
    breakdown: ScoreBreakdown
    analysis: TeamAnalysisResponse
