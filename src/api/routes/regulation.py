# src/api/routes/regulation.py
"""VGC regulations API routes."""

from fastapi import APIRouter, HTTPException

from ..db import get_db_cursor
from ..models.regulation import (
    RegulationCreate,
    RegulationDetail,
    RegulationResponse,
    RegulationUpdate,
)
from ..services import regulation_service

router = APIRouter(prefix="/regulations", tags=["regulations"])


@router.get("/", response_model=list[RegulationResponse])
def list_regulations():
    """List all regulations.

    Returns:
        List of RegulationResponse (id, name, description).
    """
    with get_db_cursor() as cursor:
        return regulation_service.list_regulations(cursor)


@router.post("/", response_model=RegulationDetail, status_code=201)
def create_regulation(body: RegulationCreate):
    """Create a new regulation with an initial Pokémon allowlist.

    Args:
        body: RegulationCreate with name, optional description, and pokemon_names.

    Returns:
        Created RegulationDetail with pokemon list.
    """
    try:
        with get_db_cursor() as cursor:
            result = regulation_service.create_regulation(
                cursor, body.name, body.description, body.pokemon_names
            )
    except ValueError as exc:
        msg = str(exc)
        if "already exists" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    return result


@router.get("/{regulation_id}", response_model=RegulationDetail)
def get_regulation(regulation_id: int):
    """Get a regulation with its full allowed Pokémon list.

    Args:
        regulation_id: DB id of the regulation.

    Returns:
        RegulationDetail with pokemon list.
    """
    try:
        with get_db_cursor() as cursor:
            return regulation_service.get_regulation(cursor, regulation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{regulation_id}", response_model=RegulationDetail)
def update_regulation(regulation_id: int, body: RegulationUpdate):
    """Update a regulation's name, description, and/or Pokémon list.

    Args:
        regulation_id: DB id of the regulation.
        body: Fields to update; pokemon_names fully replaces the existing list if provided.

    Returns:
        Updated RegulationDetail.
    """
    try:
        with get_db_cursor() as cursor:
            result = regulation_service.update_regulation(
                cursor, regulation_id, body.name, body.description, body.pokemon_names
            )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    return result


@router.delete("/{regulation_id}", status_code=204)
def delete_regulation(regulation_id: int):
    """Delete a regulation and all its pokemon associations.

    Args:
        regulation_id: DB id of the regulation.
    """
    try:
        with get_db_cursor() as cursor:
            regulation_service.delete_regulation(cursor, regulation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
