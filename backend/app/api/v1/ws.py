"""
AgentBruce — Real-Time LangGraph WebSocket Execution Endpoint

ws /api/v1/ws/investigation/{case_id}

Streams real-time step-by-step state progression across all specialized agents
(gateway -> grooming, multimedia, synthetic, osint -> timeline -> fusion -> risk)
over a persistent WebSocket connection.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.agents.graph import investigation_graph
from app.agents.state import InvestigationState

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websockets"])


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively convert non-serializable objects (UUIDs, sets, numpy types) into JSON primitives."""
    if isinstance(obj, dict):
        return {str(k): _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [_sanitize_for_json(item) for item in obj]
    elif hasattr(obj, "item"):  # handles numpy scalars
        return obj.item()
    elif hasattr(obj, "isoformat"):
        return obj.isoformat()
    elif hasattr(obj, "__str__") and not isinstance(obj, (int, float, bool, str, type(None))):
        return str(obj)
    return obj


@router.websocket("/ws/investigation/{case_id}")
async def websocket_investigation(websocket: WebSocket, case_id: str):
    """
    WebSocket endpoint for real-time investigation execution tracking.

    Protocol:
    1. Connection accepted.
    2. Client sends optional JSON payload ``{"raw_payload": {...}}`` or empty message.
    3. LangGraph workflow runs via stream, emitting step-by-step updates:
       - ``{"event": "start", "case_id": case_id}``
       - ``{"event": "step", "node": node_name, "state_update": {...}}``
       - ``{"event": "complete", "case_id": case_id, "summary": {...}}``
    """
    await websocket.accept()
    logger.info("WebSocket client connected for case_id: %s", case_id)

    try:
        # 1. Receive initial configuration/payload or set default fallback
        raw_payload = {}
        try:
            message_text = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            if message_text.strip():
                parsed = json.loads(message_text)
                raw_payload = parsed.get("raw_payload", parsed)
        except (asyncio.TimeoutError, json.JSONDecodeError):
            logger.info("No initial payload received for case %s, proceeding with default artifact.", case_id)

        if not raw_payload:
            raw_payload = {
                "metadata": {
                    "ip_address": "198.51.100.42",
                    "email": "suspect@darknet.org",
                    "username": "phantom_x",
                },
                "messages": [
                    {"sender": "phantom_x", "content": "Trust me, don't tell your parents about our chat."},
                    {"sender": "victim_a", "content": "Okay, I won't tell anyone."},
                    {"sender": "phantom_x", "content": "Meet me near the bus stop after school."},
                ],
                "yolo_objects": ["school uniform", "bus stop"],
                "ocr_text": "Bus Stop Line 4",
                "exif_metadata": {},
            }

        # 2. Build initial LangGraph state
        initial_state: InvestigationState = {
            "case_id": case_id,
            "raw_payload": raw_payload,
            "extracted_entities": [],
            "grooming_flags": [],
            "osint_hits": [],
            "media_flags": [],
            "synthetic_prob": 0.0,
            "timeline": [],
            "fused_leads": [],
            "risk_score": 0.0,
        }

        await websocket.send_json({
            "event": "start",
            "case_id": case_id,
            "message": "LangGraph multi-agent execution pipeline started.",
        })

        # 3. Stream LangGraph execution
        # Run graph stream in a thread pool to avoid blocking the asyncio event loop
        def _get_stream_chunks():
            return list(investigation_graph.stream(initial_state))

        chunks = await asyncio.to_thread(_get_stream_chunks)

        aggregated_state = dict(initial_state)

        for chunk in chunks:
            # chunk is a dict of {node_name: state_delta}
            for node_name, state_delta in chunk.items():
                sanitized_delta = _sanitize_for_json(state_delta)

                await websocket.send_json({
                    "event": "step",
                    "case_id": case_id,
                    "node": node_name,
                    "state_update": sanitized_delta,
                })
                # Small pause to allow smooth real-time animation on client UI
                await asyncio.sleep(0.3)

        # 4. Final completion message
        await websocket.send_json({
            "event": "complete",
            "case_id": case_id,
            "message": "LangGraph investigation workflow completed successfully.",
        })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected for case_id: %s", case_id)
    except Exception as exc:
        logger.error("Error during WebSocket investigation execution for %s: %s", case_id, exc)
        try:
            await websocket.send_json({
                "event": "error",
                "case_id": case_id,
                "error": str(exc),
            })
        except Exception:
            pass
