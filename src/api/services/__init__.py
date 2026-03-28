# src/api/services/__init__.py
"""API services package."""

from .type_service import (
    get_type_id,
    get_multiplier,
    calculate_damage_multiplier,
    all_multipliers_against,
)

__all__ = [
    "get_type_id",
    "get_multiplier",
    "calculate_damage_multiplier",
    "all_multipliers_against",
]
