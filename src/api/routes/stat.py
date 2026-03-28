# src/api/routes/stat.py
"""Stat calculation API routes."""

from typing import Dict
from fastapi import APIRouter, HTTPException
from ..models.stat import StatInput, StatOutput
from ..services.stat_service import calculate_stats
from ..db import get_db_connection

router = APIRouter(prefix="/stats", tags=["stats"])


@router.post("/calculate", response_model=StatOutput)
def calculate_stats_endpoint(payload: StatInput):
    """Calculate final Pokemon stats based on IVs, EVs, Nature, and Level.
    
    Defaults:
    - Level: 100
    - Nature: hardy (neutral)
    - IVs: 31 for all stats (competitive standard)
    - EVs: 0 for all stats
    
    Validation:
    - Total EVs must not exceed 510
    - Each EV must be 0-252
    - Each IV must be 0-31
    - Nature must exist in database
    - Pokemon must exist in database
    """
    try:
        with get_db_connection() as conn:
            # Cast from Dict[StatKey, int] to Dict[str, int] for service compatibility
            evs: Dict[str, int] = payload.evs.model_dump()
            ivs: Dict[str, int] = payload.ivs.model_dump()
            stats = calculate_stats(
                conn=conn,
                pokemon_name=payload.pokemon,
                level=payload.level,
                nature_name=payload.nature,
                evs=evs,
                ivs=ivs,
            )
        return stats
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
