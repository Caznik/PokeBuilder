# src/api/models/battle_log.py
"""Pydantic models for the battle logs API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator


class BattleLogCreate(BaseModel):
    """Request body for creating a battle log entry.

    Args:
        saved_team_id: Optional FK to the user's saved team.
        regulation_id: Optional FK to the regulation used.
        format: Battle format — 'singles' (3 brought) or 'vgc' (4 brought).
        brought_pokemon: Ordered list of Pokémon the player brought.
        enemy_team: List of up to 6 opponent Pokémon.
        result: Outcome of the battle.
        notes: Optional free-text notes.

    Returns:
        Validated BattleLogCreate instance.
    """

    saved_team_id: int | None = None
    regulation_id: int | None = None
    format: Literal["singles", "vgc"]
    brought_pokemon: list[str]
    enemy_team: list[str]
    enemy_brought: list[str] = []
    result: Literal["win", "loss", "tie"]
    notes: str | None = None

    @model_validator(mode="after")
    def validate_pokemon_counts(self) -> "BattleLogCreate":
        """Enforce brought_pokemon length based on format and enemy_team size.

        Returns:
            self after validation.

        Raises:
            ValueError: If brought_pokemon, enemy_team, or enemy_brought counts are invalid.
        """
        expected = 3 if self.format == "singles" else 4
        if len(self.brought_pokemon) != expected:
            raise ValueError(
                f"brought_pokemon must have exactly {expected} entries for {self.format} format, "
                f"got {len(self.brought_pokemon)}"
            )
        if not (1 <= len(self.enemy_team) <= 6):
            raise ValueError(
                f"enemy_team must have between 1 and 6 entries, got {len(self.enemy_team)}"
            )
        if self.enemy_brought and len(self.enemy_brought) != expected:
            raise ValueError(
                f"enemy_brought must have exactly {expected} entries for {self.format} format, "
                f"got {len(self.enemy_brought)}"
            )
        return self


class BattleLogOut(BaseModel):
    """Battle log record returned by the API.

    Args:
        id: Primary key.
        user_id: Owner's user id.
        saved_team_id: FK to saved_teams, or None.
        saved_team_name: Joined team name, or None.
        regulation_id: FK to regulations, or None.
        format: Battle format string.
        brought_pokemon: Pokémon the player brought.
        enemy_team: Opponent's Pokémon.
        result: Outcome string.
        notes: Optional notes.
        played_at: Timestamp of the battle.

    Returns:
        BattleLogOut instance.
    """

    id: int
    user_id: int
    saved_team_id: int | None
    saved_team_name: str | None
    regulation_id: int | None
    format: str
    brought_pokemon: list[str]
    enemy_team: list[str]
    enemy_brought: list[str]
    result: str
    notes: str | None
    played_at: datetime
    saved_team_members: list[str]
