"""
AgentBruce — Evidence Ingestion API

POST /api/v1/evidence/upload

Receives multipart evidence files, computes a streaming SHA-256 hash
for chain-of-custody integrity, rejects duplicates, persists the file
to local storage, and dispatches a Celery task for ML extraction.
"""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from io import BytesIO

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.models.schemas import Case, Evidence
from app.workers.tasks import route_evidence

logger = logging.getLogger(__name__)

router = APIRouter(tags=["evidence"])

# Size of each read chunk during streaming hash computation (64 KB).
_CHUNK_SIZE: int = 64 * 1024


@router.post(
    "/evidence/upload",
    status_code=201,
    summary="Upload forensic evidence",
    response_description="Evidence record with chain-of-custody hash",
)
async def upload_evidence(
    case_id: uuid.UUID = Form(..., description="UUID of the parent case"),
    file: UploadFile = File(..., description="Evidence binary file"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Ingest a forensic evidence file with cryptographic integrity.

    Processing pipeline:
    1. Validate the parent case exists in PostgreSQL.
    2. Stream the file in 64 KB chunks, computing SHA-256 incrementally.
    3. Reject duplicate evidence (matching SHA-256 already on record).
    4. Write the file to ``storage/evidence/{case_id}/{sha256}.bin``.
    5. Insert an ``Evidence`` record with status ``pending``.
    6. Dispatch the ``route_evidence`` Celery task for ML processing.

    Returns:
        201 Created with evidence metadata and Celery task ID.
    """
    settings = get_settings()

    # 1. Verify the parent case exists
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(
            status_code=404,
            detail=f"Case {case_id} not found.",
        )

    # 2. Stream-hash the file in chunks (prevents memory exhaustion)
    sha256_hasher = hashlib.sha256()
    buffer = BytesIO()

    while True:
        chunk = await file.read(_CHUNK_SIZE)
        if not chunk:
            break
        sha256_hasher.update(chunk)
        buffer.write(chunk)

    sha256_hex: str = sha256_hasher.hexdigest()
    file_size: int = buffer.tell()
    buffer.seek(0)

    logger.info(
        "Evidence hashed: sha256=%s  size=%d bytes  case=%s",
        sha256_hex,
        file_size,
        case_id,
    )

    # 3. Reject duplicates based on SHA-256
    duplicate = await db.execute(
        select(Evidence).where(Evidence.sha256_hash == sha256_hex)
    )
    if duplicate.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate evidence: SHA-256 {sha256_hex} already exists.",
        )

    # 4. Write file to local storage via aiofiles
    storage_dir = os.path.join(settings.STORAGE_ROOT, str(case_id))
    os.makedirs(storage_dir, exist_ok=True)

    file_name = f"{sha256_hex}.bin"
    file_path = os.path.join(storage_dir, file_name)

    async with aiofiles.open(file_path, "wb") as out:
        while True:
            chunk = buffer.read(_CHUNK_SIZE)
            if not chunk:
                break
            await out.write(chunk)

    logger.info("Evidence written to disk: %s", file_path)

    # 5. Insert Evidence record in PostgreSQL
    evidence = Evidence(
        case_id=case_id,
        sha256_hash=sha256_hex,
        file_path=file_path,
        file_type=file.content_type,
        processed_status="pending",
    )
    db.add(evidence)
    await db.flush()  # Populate evidence.id before commit
    evidence_id = evidence.id

    logger.info(
        "Evidence record created: id=%s  sha256=%s",
        evidence_id,
        sha256_hex,
    )

    # 6. Dispatch Celery task for background ML extraction
    task = route_evidence.delay(str(evidence_id))

    logger.info(
        "Celery task dispatched: task_id=%s  evidence_id=%s",
        task.id,
        evidence_id,
    )

    # 7. Return chain-of-custody receipt
    return {
        "evidence_id": str(evidence_id),
        "sha256_hash": sha256_hex,
        "file_path": file_path,
        "file_size_bytes": file_size,
        "processed_status": "pending",
        "task_id": task.id,
        "message": "Evidence ingested successfully. Processing queued.",
    }