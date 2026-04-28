# src/api/models/scoring.py
"""Pydantic models for the team scoring endpoint."""

from pydantic import BaseModel

from .team import TeamAnalysisResponse


class ScoreComponent(BaseModel):
    score: float
    reason: str


class ScoreBreakdown(BaseModel):
    coverage: ScoreComponent
    defensive: ScoreComponent
    role: ScoreComponent
    speed: ScoreComponent


class ScoreResponse(BaseModel):
    score: float
    breakdown: ScoreBreakdown
    analysis: TeamAnalysisResponse
