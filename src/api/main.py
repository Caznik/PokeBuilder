# src/api/main.py
"""Main FastAPI application entry point."""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from .routes import (
    pokemon_router, ability_router, type_router, move_router, stat_router,
    competitive_router, team_router, generation_router, scoring_router,
    optimization_router, saved_teams_router, regulation_router, auth_router,
    counter_router, battle_logs_router,
)

app = FastAPI(
    title="PokeBuilder API",
    description="REST API for querying Pokemon data from the ingested PokeAPI database",
    version="1.0.0"
)

_CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
_SESSION_SECRET = os.getenv("SESSION_SECRET_KEY", "dev-session-secret-change-in-production")

app.add_middleware(SessionMiddleware, secret_key=_SESSION_SECRET)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(pokemon_router)
app.include_router(ability_router)
app.include_router(type_router)
app.include_router(move_router)
app.include_router(stat_router)
app.include_router(competitive_router)
app.include_router(team_router)
app.include_router(generation_router)
app.include_router(scoring_router)
app.include_router(optimization_router)
app.include_router(saved_teams_router)
app.include_router(regulation_router)
app.include_router(counter_router)
app.include_router(battle_logs_router)


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to PokeBuilder API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "auth": "/auth",
            "pokemon": "/pokemon",
            "abilities": "/abilities",
            "types": "/types",
            "moves": "/moves",
            "competitive-sets": "/competitive-sets",
            "team": "/team",
            "regulations": "/regulations",
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
