"""
AgentBruce — Health Check Endpoint

GET /api/v1/health

Independently verifies connectivity to all four datastores (PostgreSQL,
Neo4j, Qdrant, Redis) and returns per-service status with latency
measurements. A single failing service does not mask the others.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import (
    get_async_engine,
    get_neo4j_driver,
    get_qdrant_client,
    get_redis_client,
)

router = APIRouter(tags=["health"])

async def _check_postgres() -> dict[str, Any]:
    """Execute SELECT 1 against PostgreSQL."""
    start = time.perf_counter()
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        return {"status": "connected", "latency_ms": round(latency, 2)}
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        return {"status": "error", "latency_ms": round(latency, 2), "detail": str(exc)}

async def _check_neo4j() -> dict[str, Any]:
    """Execute RETURN 1 against Neo4j."""
    start = time.perf_counter()
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS n")
            await result.consume()
        latency = (time.perf_counter() - start) * 1000
        return {"status": "connected", "latency_ms": round(latency, 2)}
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        return {"status": "error", "latency_ms": round(latency, 2), "detail": str(exc)}

async def _check_qdrant() -> dict[str, Any]:
    """List collections on Qdrant as a connectivity check."""
    start = time.perf_counter()
    try:
        client = get_qdrant_client()
        await client.get_collections()
        latency = (time.perf_counter() - start) * 1000
        return {"status": "connected", "latency_ms": round(latency, 2)}
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        return {"status": "error", "latency_ms": round(latency, 2), "detail": str(exc)}

async def _check_redis() -> dict[str, Any]:
    """Send PING to Redis."""
    start = time.perf_counter()
    try:
        client = get_redis_client()
        await client.ping()
        latency = (time.perf_counter() - start) * 1000
        return {"status": "connected", "latency_ms": round(latency, 2)}
    except Exception as exc:
        latency = (time.perf_counter() - start) * 1000
        return {"status": "error", "latency_ms": round(latency, 2), "detail": str(exc)}

@router.get("/health", response_model=None)
async def health_check() -> dict[str, Any]:
    """
    Comprehensive health check across all datastores.

    Returns per-service status and latency. Overall status is 'healthy'
    only when all four services report 'connected'.
    """
    services = {
        "postgres": await _check_postgres(),
        "neo4j": await _check_neo4j(),
        "qdrant": await _check_qdrant(),
        "redis": await _check_redis(),
    }

    all_connected = all(svc["status"] == "connected" for svc in services.values())

    return {
        "status": "healthy" if all_connected else "degraded",
        "services": services,
    }