"""
AgentBruce — Execution Log Emitter

Persist real pipeline events to PostgreSQL and fan them out over Redis
pub/sub so the FastAPI WebSocket endpoint can push them live to the UI.

Two code paths:
  - emit_sync(...)   → used by Celery workers (psycopg2 + redis sync)
  - emit_async(...)  → used by FastAPI request handlers (asyncpg + aioredis)

Both paths write the same row to `execution_logs` and publish the same
JSON envelope on channel  exec_logs:{case_id}.
"""

from __future__ import annotations

import json
import logging
import os
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "exec_logs"
VALID_LEVELS = {"debug", "info", "warn", "error", "success"}


def _channel(case_id: str) -> str:
    return f"{CHANNEL_PREFIX}:{case_id}"


def _normalize_level(level: str) -> str:
    level = (level or "info").lower()
    return level if level in VALID_LEVELS else "info"


def _envelope(
    case_id: str,
    level: str,
    source: str,
    message: str,
    evidence_id: Optional[str] = None,
    extra: Optional[Mapping[str, Any]] = None,
    row_id: Optional[str] = None,
    created_at: Optional[datetime] = None,
) -> dict:
    return {
        "id": row_id,
        "case_id": case_id,
        "evidence_id": evidence_id,
        "level": _normalize_level(level),
        "source": source or "system",
        "message": message,
        "extra": dict(extra) if extra else None,
        "created_at": (created_at or datetime.now(timezone.utc)).isoformat(),
    }


# ---------------------------------------------------------------------------
# Sync path (Celery workers)
# ---------------------------------------------------------------------------

def _sync_dsn() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql://bruce:bruceforensics@localhost:5435/agentbruce",
    )
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    if "@postgres:5432" in url or "@postgres:" in url:
        url = url.replace("@postgres:5432", "@localhost:5435").replace(
            "@postgres:", "@localhost:5435"
        )
    return url


def _sync_redis_url() -> str:
    url = os.getenv("REDIS_URL", "redis://localhost:6381/0")
    if "redis://redis:6379" in url or "@redis:" in url:
        url = url.replace("redis://redis:6379", "redis://localhost:6381").replace(
            "@redis:", "@localhost:6381"
        )
    return url


def emit_sync(
    case_id: str,
    message: str,
    *,
    level: str = "info",
    source: str = "system",
    evidence_id: Optional[str] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> None:
    """Persist a log row (sync) and publish it to Redis. Safe to call anywhere."""
    level = _normalize_level(level)
    case_id = str(case_id)
    evidence_id = str(evidence_id) if evidence_id else None

    row_id: Optional[str] = None
    created_at: Optional[datetime] = None

    # 1) DB write (best effort)
    try:
        import psycopg2
        from psycopg2.extras import Json

        conn = psycopg2.connect(_sync_dsn())
        try:
            conn.autocommit = True
            with conn.cursor() as cur:
                row_id = str(_uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO execution_logs
                        (id, case_id, evidence_id, level, source, message, extra)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING created_at
                    """,
                    (
                        row_id,
                        case_id,
                        evidence_id,
                        level,
                        source,
                        message,
                        Json(dict(extra)) if extra else None,
                    ),
                )
                fetched = cur.fetchone()
                if fetched and fetched[0]:
                    created_at = fetched[0]
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("emit_sync: DB write failed (%s): %s", level, exc)

    # 2) Pub/Sub broadcast (best effort)
    envelope = _envelope(
        case_id=case_id,
        level=level,
        source=source,
        message=message,
        evidence_id=evidence_id,
        extra=extra,
        row_id=row_id,
        created_at=created_at,
    )
    try:
        import redis as sync_redis

        client = sync_redis.Redis.from_url(_sync_redis_url(), decode_responses=True)
        client.publish(_channel(case_id), json.dumps(envelope))
    except Exception as exc:  # noqa: BLE001
        logger.warning("emit_sync: redis publish failed: %s", exc)


# ---------------------------------------------------------------------------
# Async path (FastAPI handlers)
# ---------------------------------------------------------------------------

async def emit_async(
    case_id: str,
    message: str,
    *,
    level: str = "info",
    source: str = "system",
    evidence_id: Optional[str] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> None:
    """Persist a log row (async SQLAlchemy) and publish it on Redis."""
    from sqlalchemy import insert

    from app.core.database import (
        get_async_engine,
        get_redis_client,
        is_postgres_available,
    )
    from app.models.schemas import ExecutionLog

    level = _normalize_level(level)
    case_id = str(case_id)
    evidence_id = str(evidence_id) if evidence_id else None

    row_id: Optional[str] = None
    created_at: Optional[datetime] = None

    if is_postgres_available():
        try:
            engine = get_async_engine()
            async with engine.begin() as conn:
                row_id = str(_uuid.uuid4())
                result = await conn.execute(
                    insert(ExecutionLog)
                    .values(
                        id=_uuid.UUID(row_id),
                        case_id=_uuid.UUID(case_id),
                        evidence_id=_uuid.UUID(evidence_id) if evidence_id else None,
                        level=level,
                        source=source,
                        message=message,
                        extra=dict(extra) if extra else None,
                    )
                    .returning(ExecutionLog.created_at)
                )
                fetched = result.first()
                if fetched and fetched[0]:
                    created_at = fetched[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("emit_async: DB write failed: %s", exc)

    envelope = _envelope(
        case_id=case_id,
        level=level,
        source=source,
        message=message,
        evidence_id=evidence_id,
        extra=extra,
        row_id=row_id,
        created_at=created_at,
    )
    try:
        client = get_redis_client()
        await client.publish(_channel(case_id), json.dumps(envelope))
    except Exception as exc:  # noqa: BLE001
        logger.warning("emit_async: redis publish failed: %s", exc)
