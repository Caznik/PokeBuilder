# src/api/models/stat.py
"""Pydantic models for stat calculation."""

from pydantic import BaseModel, Field, field_validator


class StatEvs(BaseModel):
    """EV distribution with defaults of 0."""
    hp: int = Field(0, ge=0, le=252)
    attack: int = Field(0, ge=0, le=252)
    defense: int = Field(0, ge=0, le=252)
    sp_attack: int = Field(0, ge=0, le=252)
    sp_defense: int = Field(0, ge=0, le=252)
    speed: int = Field(0, ge=0, le=252)

    @field_validator("*")
    @classmethod
    def _validate_total(cls, v, info):
        return v  # per-field range is enforced by Field(ge=0, le=252)

    def model_post_init(self, __context):
        total = sum(self.model_dump().values())
        if total > 510:
            raise ValueError("Total EVs may not exceed 510")


class StatIvs(BaseModel):
    """IV distribution with defaults of 31."""
    hp: int = Field(31, ge=0, le=31)
    attack: int = Field(31, ge=0, le=31)
    defense: int = Field(31, ge=0, le=31)
    sp_attack: int = Field(31, ge=0, le=31)
    sp_defense: int = Field(31, ge=0, le=31)
    speed: int = Field(31, ge=0, le=31)


class StatInput(BaseModel):
    """Payload for stat calculation."""
    pokemon: str
    level: int = Field(100, ge=1, le=100)
    nature: str = "hardy"
    evs: StatEvs = Field(default_factory=StatEvs)
    ivs: StatIvs = Field(default_factory=StatIvs)


class StatOutput(BaseModel):
    """Returned final stats."""
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int