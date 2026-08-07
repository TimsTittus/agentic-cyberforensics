"""
AgentBruce — Celery Application Configuration

Initializes the Celery distributed task queue using Redis as both
the message broker and result backend.  Task modules are auto-
discovered so new workers only need to be added under `app.workers`.

Usage (worker process):
    celery -A app.core.celery_app worker --loglevel=info -Q evidence
"""

from __future__ import annotations

import os

from celery import Celery

# ---------------------------------------------------------------------------
# Read broker URL from Settings (same REDIS_URL used by the async client).
# ---------------------------------------------------------------------------
from app.core.config import get_settings

settings = get_settings()
_REDIS_URL: str = settings.REDIS_URL

celery_app = Celery("agentbruce")

celery_app.conf.update(
    # Transport
    broker_url=_REDIS_URL,
    result_backend=_REDIS_URL,

    # Serialization — JSON-only for forensic auditability
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task routing — isolate evidence processing on its own queue
    task_routes={
        "route_evidence": {"queue": "evidence"},
    },
)

celery_app.autodiscover_tasks(["app.workers"])