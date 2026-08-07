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
from app.models.schemas import Case

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

@router.get(
    "/cases",
    response_model=List[CaseResponse],
    summary="List all cases",
)
async def list_cases(db: AsyncSession = Depends(get_db_session)):
    """Fetch all cases ordered by creation date descending."""
    result = await db.execute(select(Case).order_by(Case.created_at.desc()))
    cases = result.scalars().all()
    
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