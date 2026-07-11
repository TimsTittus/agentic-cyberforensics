"""
AgentBruce — Async Database Connection Managers

Independent connection lifecycle managers for:
  • PostgreSQL  (SQLAlchemy AsyncEngine)
  • Neo4j       (Official AsyncGraphDatabase driver)
  • Qdrant      (AsyncQdrantClient)
  • Redis       (redis.asyncio)

Each manager exposes connect() / disconnect() hooks consumed by
the FastAPI lifespan context manager in main.py.
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

import redis.asyncio as aioredis
from neo4j import AsyncGraphDatabase
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# PostgreSQL — SQLAlchemy Async Engine

_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


async def connect_postgres() -> None:
    """Create the async engine and session factory."""
    global _async_engine, _async_session_factory

    settings = get_settings()
    _async_engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=settings.DEBUG,
    )
    _async_session_factory = async_sessionmaker(
        bind=_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info("PostgreSQL async engine created.")

async def disconnect_postgres() -> None:
    """Dispose of the async engine and close all pooled connections."""
    global _async_engine, _async_session_factory

    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("PostgreSQL async engine disposed.")

def get_async_engine() -> AsyncEngine:
    """Return the active async engine (raises if not connected)."""
    if _async_engine is None:
        raise RuntimeError("PostgreSQL engine not initialized. Call connect_postgres() first.")
    return _async_engine

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields a scoped async session."""
    if _async_session_factory is None:
        raise RuntimeError("PostgreSQL session factory not initialized.")
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

# Neo4j — AsyncGraphDatabase Driver

_neo4j_driver = None

# Cypher constraints executed once on startup to enforce graph integrity.
NEO4J_CONSTRAINTS = [
    "CREATE CONSTRAINT suspect_id_unique IF NOT EXISTS FOR (s:Suspect) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT victim_id_unique IF NOT EXISTS FOR (v:Victim) REQUIRE v.id IS UNIQUE",
    "CREATE CONSTRAINT account_platform_id_unique IF NOT EXISTS FOR (a:Account) REQUIRE a.platform_id IS UNIQUE",
    "CREATE CONSTRAINT evidence_sha256_unique IF NOT EXISTS FOR (e:Evidence) REQUIRE e.sha256 IS UNIQUE",
]

async def connect_neo4j() -> None:
    """Create the Neo4j async driver, verify connectivity, and apply constraints."""
    global _neo4j_driver

    settings = get_settings()
    _neo4j_driver = AsyncGraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD.get_secret_value()),
    )

    # Verify the connection is live
    await _neo4j_driver.verify_connectivity()
    logger.info("Neo4j driver connected and verified.")

    # Apply uniqueness constraints
    async with _neo4j_driver.session() as session:
        for cypher in NEO4J_CONSTRAINTS:
            await session.run(cypher)
            logger.info("Neo4j constraint applied: %s", cypher.split("FOR")[0].strip())

async def disconnect_neo4j() -> None:
    """Close the Neo4j driver."""
    global _neo4j_driver

    if _neo4j_driver is not None:
        await _neo4j_driver.close()
        _neo4j_driver = None
        logger.info("Neo4j driver closed.")

def get_neo4j_driver():
    """Return the active Neo4j driver (raises if not connected)."""
    if _neo4j_driver is None:
        raise RuntimeError("Neo4j driver not initialized. Call connect_neo4j() first.")
    return _neo4j_driver

# Qdrant — AsyncQdrantClient

_qdrant_client: AsyncQdrantClient | None = None

async def connect_qdrant() -> None:
    """Initialize the Qdrant async client and verify connectivity."""
    global _qdrant_client

    settings = get_settings()
    _qdrant_client = AsyncQdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )

    # Verify connectivity by listing collections
    await _qdrant_client.get_collections()
    logger.info("Qdrant client connected and verified.")

async def disconnect_qdrant() -> None:
    """Close the Qdrant client."""
    global _qdrant_client

    if _qdrant_client is not None:
        await _qdrant_client.close()
        _qdrant_client = None
        logger.info("Qdrant client closed.")

def get_qdrant_client() -> AsyncQdrantClient:
    """Return the active Qdrant client (raises if not connected)."""
    if _qdrant_client is None:
        raise RuntimeError("Qdrant client not initialized. Call connect_qdrant() first.")
    return _qdrant_client

# Redis — redis.asyncio

_redis_client: aioredis.Redis | None = None

async def connect_redis() -> None:
    """Create the Redis async client and verify connectivity."""
    global _redis_client

    settings = get_settings()
    _redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
    )

    # Verify connectivity
    await _redis_client.ping()
    logger.info("Redis client connected and verified.")

async def disconnect_redis() -> None:
    """Close the Redis client."""
    global _redis_client

    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis client closed.")

def get_redis_client() -> aioredis.Redis:
    """Return the active Redis client (raises if not connected)."""
    if _redis_client is None:
        raise RuntimeError("Redis client not initialized. Call connect_redis() first.")
    return _redis_client