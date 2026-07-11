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
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
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