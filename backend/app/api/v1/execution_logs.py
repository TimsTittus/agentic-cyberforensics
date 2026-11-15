"""
AgentBruce — Execution Logs API

GET /api/v1/cases/{case_id}/execution-logs        historical log rows
WS  /api/v1/ws/execution-logs/{case_id}           live stream (Redis sub)

Both endpoints are powered by the `execution_logs` table + the
`exec_logs:{case_id}` Redis pub/sub channel written by
`app.core.execution_log.emit_sync` / `emit_async`.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session, get_redis_client
from app.core.execution_log import CHANNEL_PREFIX
from app.models.schemas import ExecutionLog

logger = logging.getLogger(__name__)

router = APIRouter(tags=["execution-logs"])


class ExecutionLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    evidence_id: Optional[uuid.UUID] = None
    level: str
    source: str
    message: str
    extra: Optional[dict] = None
    created_at: str


@router.get(
    "/cases/{case_id}/execution-logs",
    response_model=List[ExecutionLogItem],
    summary="Historical execution-log timeline for a case",
)
async def list_case_logs(
    case_id: uuid.UUID,
    limit: int = Query(500, ge=1, le=5000),
    after: Optional[str] = Query(None, description="ISO timestamp — return only rows after this"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Return the log rows for this case ordered oldest-first so the UI
    can render them as a chronological terminal stream.
    """
    stmt = select(ExecutionLog).where(ExecutionLog.case_id == case_id)
    if after:
        from datetime import datetime
        try:
            after_dt = datetime.fromisoformat(after.replace("Z", "+00:00"))
            stmt = stmt.where(ExecutionLog.created_at > after_dt)
        except ValueError:
            raise HTTPException(400, "Invalid `after` timestamp")

    stmt = stmt.order_by(ExecutionLog.created_at.asc()).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()

    return [
        ExecutionLogItem(
            id=r.id,
            case_id=r.case_id,
            evidence_id=r.evidence_id,
            level=r.level,
            source=r.source,
            message=r.message,
            extra=r.extra,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]


@router.websocket("/ws/execution-logs/{case_id}")
async def stream_case_logs(websocket: WebSocket, case_id: str):
    """
    Live-stream log rows for a case as the Celery worker and FastAPI
    handlers emit them. Backed by Redis pub/sub channel
    ``exec_logs:{case_id}``.
    """
    await websocket.accept()

    channel = f"{CHANNEL_PREFIX}:{case_id}"

    try:
        redis = get_redis_client()
    except Exception as exc:
        logger.warning("WS logs: redis unavailable for case %s: %s", case_id, exc)
        await websocket.send_json({
            "level": "error",
            "source": "system",
            "message": f"Live stream unavailable: {exc}",
        })
        await websocket.close()
        return

    pubsub = redis.pubsub()
    await pubsub.subscribe(channel)

    await websocket.send_json({
        "level": "info",
        "source": "stream",
        "message": f"Subscribed to live execution stream for case {case_id}",
    })

    disconnected = asyncio.Event()

    async def _watch_client():
        """Trip `disconnected` as soon as the client closes or errors out."""
        try:
            while not disconnected.is_set():
                await websocket.receive_text()
        except Exception:
            pass
        finally:
            disconnected.set()

    watcher = asyncio.create_task(_watch_client())

    try:
        while not disconnected.is_set():
            # Poll pubsub with a short timeout so we can react to disconnects
            raw = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if raw is None:
                continue

            data = raw.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="replace")
            try:
                payload = json.loads(data) if isinstance(data, str) else data
            except Exception:
                payload = {"level": "info", "source": "stream", "message": str(data)}

            try:
                await websocket.send_json(payload)
            except Exception:
                break
    except Exception as exc:
        logger.warning("WS logs: stream error for case %s: %s", case_id, exc)
    finally:
        disconnected.set()
        watcher.cancel()
        try:
            await pubsub.unsubscribe(channel)
        except Exception:
            pass
        try:
            close_fn = getattr(pubsub, "aclose", None) or getattr(pubsub, "close", None)
            if close_fn is not None:
                res = close_fn()
                if asyncio.iscoroutine(res):
                    await res
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
