"""
AgentBruce — Cases API Endpoint

GET  /api/v1/cases — Query open and active cases from PostgreSQL.
POST /api/v1/cases — Create a new investigation case record.
"""

from __future__ import annotations

import logging
from typing import List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models.schemas import Case, Evidence

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cases"])

class CaseCreate(BaseModel):
    title: str
    risk_level: Optional[str] = "medium"

class CaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: str
    risk_level: str
    created_at: str
    updated_at: Optional[str] = None

INITIAL_SEED_CASES = [
    {
        "id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        "title": "Operation Nighthawk – Telegram Network",
        "status": "in_progress",
        "risk_level": "critical",
    },
    {
        "id": uuid.UUID("660e8400-e29b-41d4-a716-446655440001"),
        "title": "Case Bravo – Discord Server Infiltration",
        "status": "open",
        "risk_level": "high",
    },
    {
        "id": uuid.UUID("770e8400-e29b-41d4-a716-446655440002"),
        "title": "Operation Sentinel – Image Forensics Cluster",
        "status": "in_progress",
        "risk_level": "high",
    },
    {
        "id": uuid.UUID("880e8400-e29b-41d4-a716-446655440003"),
        "title": "Case Delta – Encrypted Channel Analysis",
        "status": "open",
        "risk_level": "medium",
    },
    {
        "id": uuid.UUID("990e8400-e29b-41d4-a716-446655440004"),
        "title": "Operation Phantom – Dark Web Marketplace",
        "status": "in_progress",
        "risk_level": "critical",
    },
    {
        "id": uuid.UUID("aa0e8400-e29b-41d4-a716-446655440005"),
        "title": "Case Echo – Social Engineering Vector",
        "status": "closed",
        "risk_level": "low",
    },
]

@router.get(
    "/cases",
    response_model=List[CaseResponse],
    summary="List all cases",
)
async def list_cases(db: AsyncSession = Depends(get_db_session)):
    """Fetch all cases ordered by creation date descending. Auto-seeds missing baseline cases."""
    result = await db.execute(select(Case).order_by(Case.created_at.desc()))
    cases = list(result.scalars().all())
    
    existing_ids = {c.id for c in cases}
    seeded = False
    for seed in INITIAL_SEED_CASES:
        if seed["id"] not in existing_ids:
            db.add(
                Case(
                    id=seed["id"],
                    title=seed["title"],
                    status=seed["status"],
                    risk_level=seed["risk_level"],
                )
            )
            seeded = True

    if seeded:
        await db.commit()
        result = await db.execute(select(Case).order_by(Case.created_at.desc()))
        cases = list(result.scalars().all())

    return [
        CaseResponse(
            id=c.id,
            title=c.title,
            status=c.status,
            risk_level=c.risk_level,
            created_at=c.created_at.isoformat() if c.created_at else "",
            updated_at=c.updated_at.isoformat() if c.updated_at else None,
        )
        for c in cases
    ]

@router.post(
    "/cases",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new case",
)
async def create_case(
    payload: CaseCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new investigation case in PostgreSQL."""
    new_case = Case(
        title=payload.title,
        status="open",
        risk_level=payload.risk_level or "medium",
    )
    db.add(new_case)
    await db.commit()
    await db.refresh(new_case)
    
    return CaseResponse(
        id=new_case.id,
        title=new_case.title,
        status=new_case.status,
        risk_level=new_case.risk_level,
        created_at=new_case.created_at.isoformat() if new_case.created_at else "",
        updated_at=new_case.updated_at.isoformat() if new_case.updated_at else None,
    )

class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    sha256_hash: str
    file_path: str
    file_type: Optional[str] = None
    processed_status: str
    ingested_at: str

@router.get(
    "/cases/{case_id}/evidence",
    response_model=List[EvidenceResponse],
    summary="Get all evidence items for a case",
)
async def get_case_evidence(
    case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Fetch all evidence records attached to a case."""
    case_res = await db.execute(select(Case).where(Case.id == case_id))
    if case_res.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Case not found")

    result = await db.execute(
        select(Evidence).where(Evidence.case_id == case_id).order_by(Evidence.ingested_at.desc())
    )
    items = result.scalars().all()
    return [
        EvidenceResponse(
            id=item.id,
            case_id=item.case_id,
            sha256_hash=item.sha256_hash,
            file_path=item.file_path,
            file_type=item.file_type,
            processed_status=item.processed_status,
            ingested_at=item.ingested_at.isoformat() if item.ingested_at else "",
        )
        for item in items
    ]