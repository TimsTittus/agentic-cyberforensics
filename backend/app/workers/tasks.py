"""
AgentBruce — Celery Worker Tasks

Background tasks executed by Celery workers outside the FastAPI
async event loop.  All database access uses synchronous psycopg2
connections since Celery workers are sync processes.
"""

from __future__ import annotations

import logging
import os

import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)

def _get_sync_dsn() -> str:
    """
    Convert the async DATABASE_URL to a synchronous psycopg2 DSN.

    The env var uses ``postgresql+asyncpg://…`` for SQLAlchemy async,
    but Celery workers need plain ``postgresql://…`` for psycopg2.
    """
    url = os.getenv("DATABASE_URL", "")
    return url.replace("postgresql+asyncpg://", "postgresql://")

@celery_app.task(name="route_evidence", bind=True, max_retries=3)
def route_evidence(self, evidence_id: str) -> dict:
    """
    Transition evidence status to 'processing' and prepare for ML extraction.

    This task is dispatched by the ingestion endpoint after a file has been
    hashed, persisted to disk, and recorded in PostgreSQL.

    Steps:
        1. Connect to PostgreSQL (sync) and update ``processed_status``
           from ``'pending'`` → ``'processing'``.
        2. Fetch the ``file_path`` for downstream ML pipeline consumption.
        3. Return a receipt dict for result-backend inspection.

    Args:
        evidence_id: UUID string of the evidence record.

    Returns:
        dict with ``evidence_id``, ``file_path``, and ``status``.
    """
    dsn = _get_sync_dsn()

    logger.info(
        "route_evidence started: evidence_id=%s",
        evidence_id,
    )

    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = False

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Update status to 'processing'
            cur.execute(
                """
                UPDATE evidence
                   SET processed_status = 'processing'
                 WHERE id = %s
                   AND processed_status = 'pending'
             RETURNING id, file_path, processed_status
                """,
                (evidence_id,),
            )
            row = cur.fetchone()

            if row is None:
                conn.rollback()
                logger.warning(
                    "Evidence %s not found or already processing.",
                    evidence_id,
                )
                return {
                    "evidence_id": evidence_id,
                    "status": "skipped",
                    "detail": "Record not found or not in 'pending' state.",
                }

            conn.commit()

        file_path = row["file_path"]

        logger.info(
            "Evidence %s transitioned to 'processing'. "
            "File path ready for ML extraction: %s",
            evidence_id,
            file_path,
        )

        return {
            "evidence_id": evidence_id,
            "file_path": file_path,
            "status": "processing",
        }

    except Exception as exc:
        logger.error(
            "route_evidence failed for %s: %s",
            evidence_id,
            exc,
        )
        raise self.retry(exc=exc, countdown=5)

    finally:
        if "conn" in locals() and conn is not None:
            conn.close()