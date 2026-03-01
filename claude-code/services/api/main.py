"""
FastAPI application -- the REST API for the Sommelier platform.

Provides endpoints for:
- Wine search and CRUD (/v1/wines)
- Bi-temporal price queries (/v1/prices)
- Recommendations (/v1/recommend)
- LLM agent chat (/v1/chat)
- Personal consumption history (/v1/consumption)

TODO: Implement once PostgreSQL schema and ingestion pipeline are in place.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Sommelier API",
    description="Wine data analytics platform -- front-office engineering demo",
    version="0.1.0",
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict:
    # TODO: check DB connectivity
    return {"status": "ok"}
