"""
AgentBruce — SQLAlchemy ORM Models

PostgreSQL table definitions for the forensic case management layer.
Tables are auto-created via Base.metadata.create_all() during startup.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass



class Case(Base):
    """
    A forensic investigation case.

    Tracks the overall investigation status and computed risk level
    derived from the agentic analysis pipeline.
    """

    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default="open",
        server_default="open",
    )
    risk_level: Mapped[str] = mapped_column(
        String(50),
        default="low",
        server_default="low",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    # Relationships
    evidence_items: Mapped[list[Evidence]] = relationship(
        "Evidence",
        back_populates="case",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'in_progress', 'closed', 'archived')",
            name="ck_cases_status",
        ),
        CheckConstraint(
            "risk_level IN ('low', 'medium', 'high', 'critical')",
            name="ck_cases_risk_level",
        ),
    )

    def __repr__(self) -> str:
        return f"<Case(id={self.id}, title='{self.title}', status='{self.status}')>"


class Evidence(Base):
    """
    A piece of digital evidence linked to a case.

    Each evidence record tracks the file location, integrity hash,
    and processing status through the ML pipeline.
    """

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    sha256_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    processed_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        server_default="pending",
    )
    extracted_data: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    case: Mapped[Case] = relationship("Case", back_populates="evidence_items")

    __table_args__ = (
        CheckConstraint(
            "processed_status IN ('pending', 'processing', 'completed', 'failed')",
            name="ck_evidence_processed_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<Evidence(id={self.id}, sha256='{self.sha256_hash[:12]}...', status='{self.processed_status}')>"


class ExecutionLog(Base):
    """
    Append-only timeline of real pipeline events for a case:
    ingestion, hashing, extraction, Qdrant/Neo4j indexing, errors, etc.

    Powers the Live Execution terminal — history + live stream.
    """

    __tablename__ = "execution_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    level: Mapped[str] = mapped_column(String(16), default="info", server_default="info")
    source: Mapped[str] = mapped_column(String(64), default="system", server_default="system")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "level IN ('debug', 'info', 'warn', 'error', 'success')",
            name="ck_execution_logs_level",
        ),
        Index("ix_execution_logs_case_created", "case_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ExecutionLog(case={self.case_id}, level={self.level}, src={self.source})>"


# ---------------------------------------------------------------------------
# Pydantic response-only models (not persisted ORM tables)
# ---------------------------------------------------------------------------
from pydantic import BaseModel as PydanticBase


class CrossCaseMatchAlert(PydanticBase):
    """Ephemeral alert surfaced when a cross-case entity overlap is detected."""

    alert_id: str
    current_case_id: str
    matched_case_id: str
    matched_case_title: str
    matched_entity_type: str
    matched_entity_value: str
    confidence_score: float
    linking_reason: str