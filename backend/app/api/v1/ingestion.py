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
from app.core.execution_log import emit_async
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

    await emit_async(
        str(case_id),
        f"Evidence upload received — filename='{file.filename}', content_type={file.content_type or 'unknown'}",
        level="info",
        source="gateway",
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

    await emit_async(
        str(case_id),
        f"Chain-of-custody SHA-256 computed: {sha256_hex[:16]}… ({file_size:,} bytes)",
        level="info",
        source="hash",
        extra={"sha256": sha256_hex, "bytes": file_size},
    )

    # 3. Reject duplicates based on SHA-256
    duplicate = await db.execute(
        select(Evidence).where(Evidence.sha256_hash == sha256_hex)
    )
    if duplicate.scalar_one_or_none() is not None:
        await emit_async(
            str(case_id),
            f"Duplicate rejected: SHA-256 {sha256_hex[:16]}… already on record",
            level="warn",
            source="hash",
        )
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

    await emit_async(
        str(case_id),
        f"Evidence persisted to {file_path}",
        level="info",
        source="storage",
    )

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

    await emit_async(
        str(case_id),
        f"Celery task dispatched: task_id={task.id}, evidence_id={evidence_id}",
        level="info",
        source="celery",
        evidence_id=str(evidence_id),
        extra={"task_id": task.id},
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

@router.delete(
    "/evidence/{evidence_id}",
    summary="Delete forensic evidence",
)
async def delete_evidence(
    evidence_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Remove evidence record from PostgreSQL, delete disk file, and detach/delete the corresponding node from Neo4j.
    """
    # 1. Fetch the evidence record
    result = await db.execute(select(Evidence).where(Evidence.id == evidence_id))
    evidence = result.scalar_one_or_none()
    if evidence is None:
        raise HTTPException(status_code=404, detail="Evidence not found")

    # 2. Delete the local file from disk if it exists
    if evidence.file_path and os.path.exists(evidence.file_path):
        try:
            os.remove(evidence.file_path)
            logger.info("Deleted evidence file: %s", evidence.file_path)
        except Exception as err:
            logger.warning("Failed to delete physical file: %s", err)

    # 3. Detach and delete from Neo4j
    try:
        from app.core.database import get_neo4j_driver
        driver = get_neo4j_driver()
        async with driver.session() as session:
            await session.run("MATCH (e:Evidence {id: $ev_id}) DETACH DELETE e", ev_id=str(evidence_id))
            logger.info("Deleted evidence node from Neo4j: %s", evidence_id)
    except Exception as neo_err:
        logger.warning("Failed to delete Neo4j node for evidence %s: %s", evidence_id, neo_err)

    # 4. Remove from PostgreSQL
    case_id_for_log = evidence.case_id
    await db.delete(evidence)
    await db.commit()

    try:
        await emit_async(
            str(case_id_for_log),
            f"Evidence {evidence_id} deleted (file + Postgres + Neo4j)",
            level="warn",
            source="gateway",
            evidence_id=str(evidence_id),
        )
    except Exception:
        pass

    return {"message": "Evidence deleted successfully."}