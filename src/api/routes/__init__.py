# src/api/routes/__init__.py
"""API routes package."""

from .pokemon import router as pokemon_router
from .ability import router as ability_router
from .type import router as type_router

__all__ = ["pokemon_router", "ability_router", "type_router"]