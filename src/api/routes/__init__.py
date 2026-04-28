# src/api/routes/__init__.py
"""API routes package."""

from .pokemon import router as pokemon_router
from .ability import router as ability_router
from .type import router as type_router
from .move import router as move_router
from .stat import router as stat_router
from .competitive import router as competitive_router
from .team import router as team_router
from .generation import router as generation_router
from .scoring import router as scoring_router

__all__ = ["pokemon_router", "ability_router", "type_router", "move_router",
           "stat_router", "competitive_router", "team_router", "generation_router",
           "scoring_router"]