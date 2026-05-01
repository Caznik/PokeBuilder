# src/api/main.py
"""Main FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import (
    pokemon_router, ability_router, type_router, move_router, stat_router,
    competitive_router, team_router, generation_router, scoring_router,
    optimization_router, saved_teams_router,
)

app = FastAPI(
    title="PokeBuilder API",
    description="REST API for querying Pokemon data from the ingested PokeAPI database",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
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


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to PokeBuilder API",
        "version": "1.0.0",
        "documentation": "/docs",
        "endpoints": {
            "pokemon": "/pokemon",
            "abilities": "/abilities",
            "types": "/types",
            "moves": "/moves",
            "competitive-sets": "/competitive-sets",
            "team": "/team",
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
