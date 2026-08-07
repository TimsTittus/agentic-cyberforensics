"""
AgentBruce — FastAPI Application Entry Point

Manages the full application lifecycle:
  • Startup:  Connect all databases, create PostgreSQL tables,
              apply Neo4j constraints.
  • Shutdown: Gracefully disconnect all database connections.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.v1.cases import router as cases_router
from app.api.v1.graph import router as graph_router
from app.api.v1.health import router as health_router
from app.api.v1.ingestion import router as ingestion_router
from app.core.config import get_settings
from app.core.database import (
    connect_neo4j,
    connect_postgres,
    connect_qdrant,
    connect_redis,
    disconnect_neo4j,
    disconnect_postgres,
    disconnect_qdrant,
    disconnect_redis,
    get_async_engine,
)
from app.models.schemas import Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.

    Startup: Connect to all datastores and initialize schemas.
    Shutdown: Gracefully disconnect all datastores.
    """
    settings = get_settings()
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    # Startup
    # Connect to all datastores
    await connect_postgres()
    await connect_neo4j()    # Also applies uniqueness constraints
    await connect_qdrant()
    await connect_redis()

    # Create PostgreSQL tables if they don't exist
    engine: AsyncEngine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("PostgreSQL tables verified/created.")

    logger.info("All database connections established. System ready.")

    yield  # Application is running

    # Shutdown
    logger.info("Shutting down %s...", settings.APP_NAME)
    await disconnect_redis()
    await disconnect_qdrant()
    await disconnect_neo4j()
    await disconnect_postgres()
    logger.info("All database connections closed. Goodbye.")

# FastAPI Application

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Agentic Cyberforensics Investigation Operating System",
    lifespan=lifespan,
)

# Mount API routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(ingestion_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(graph_router, prefix="/api/v1")

@app.get("/", tags=["root"])
async def root():
    """Root endpoint — returns application metadata."""
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/v1/health",
    }