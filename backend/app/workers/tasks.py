"""
AgentBruce — Celery Worker Tasks

Background tasks executed by Celery workers outside the FastAPI
async event loop.  All database access uses synchronous psycopg2
connections since Celery workers are sync processes.
"""

from __future__ import annotations

import json
import logging
import os

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from app.core.celery_app import celery_app
from app.workers.extractors import process_file

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
    Transition evidence status to 'processing', execute ML extraction pipeline,
    and persist structured JSON results to PostgreSQL.

    Args:
        evidence_id: UUID string of the evidence record.

    Returns:
        dict with ``evidence_id``, ``file_path``, ``status``, and ``artifact``.
    """
    dsn = _get_sync_dsn()

    logger.info(
        "route_evidence started: evidence_id=%s",
        evidence_id,
    )

    conn = None
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = False

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Update status to 'processing' and fetch file_path and file_type
            cur.execute(
                """
                UPDATE evidence
                   SET processed_status = 'processing'
                  WHERE id = %s
                    AND processed_status = 'pending'
              RETURNING id, file_path, file_type, processed_status
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
        file_type = row.get("file_type")

        logger.info(
            "Evidence %s transitioned to 'processing'. "
            "Executing process_file: path=%s, type=%s",
            evidence_id,
            file_path,
            file_type,
        )

        # 2. Run ML extraction pipeline wrapper
        artifact = process_file(file_path=file_path, file_type=file_type)

        # 3. Update PostgreSQL with extracted_data and status='completed'
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE evidence
                   SET processed_status = 'completed',
                       extracted_data = %s
                  WHERE id = %s
                """,
                (Json(artifact), evidence_id),
            )
            conn.commit()

        logger.info(
            "Evidence %s successfully parsed and updated to 'completed'.",
            evidence_id,
        )

        return {
            "evidence_id": evidence_id,
            "file_path": file_path,
            "status": "completed",
            "artifact": artifact,
        }

    except Exception as exc:
        logger.error(
            "route_evidence failed for %s: %s",
            evidence_id,
            exc,
            exc_info=True,
        )
        if conn is not None:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE evidence
                           SET processed_status = 'failed'
                         WHERE id = %s
                        """,
                        (evidence_id,),
                    )
                    conn.commit()
            except Exception as update_err:
                logger.error("Failed to set status to 'failed' for %s: %s", evidence_id, update_err)

        raise self.retry(exc=exc, countdown=5)

    finally:
        if conn is not None:
            conn.close()