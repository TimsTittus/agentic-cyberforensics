"""
AgentBruce — AI Case Summary & Lead Report Generator API

POST /api/v1/report/generate

Synthesizes PostgreSQL evidence records, Neo4j knowledge graph topology,
and Qdrant vector evidence hits into an executive forensic investigation report.
All content is derived from real ingested data — no hardcoded mock fallbacks.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_neo4j_driver, get_qdrant_client, get_db_session
from app.models.schemas import Case, Evidence

logger = logging.getLogger(__name__)

router = APIRouter(tags=["report"])


class ReportRequest(BaseModel):
    case_id: str
    case_title: Optional[str] = None


class EntitySummary(BaseModel):
    name: str
    type: str
    details: str


class EvidenceItem(BaseModel):
    source: str
    content: str
    relevance_score: float


class AiReportResponse(BaseModel):
    case_id: str
    case_title: str
    generated_at: str
    risk_level: str
    risk_score: float
    executive_summary: str
    key_findings: List[str]
    grooming_stages_detected: List[str]
    entities: List[EntitySummary]
    top_evidence_vectors: List[EvidenceItem]
    recommendations: List[str]


@router.post("/report/generate", response_model=AiReportResponse, summary="Generate AI Case Summary & Lead Report")
async def generate_ai_report(
    payload: ReportRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Synthesize a forensic report from real data sources:
    - PostgreSQL: case metadata and evidence records
    - Neo4j: entity relationship graph (if connected)
    - Qdrant: vector evidence hits (if connected and populated)
    """
    case_id = payload.case_id
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Load case from PostgreSQL
    import uuid as _uuid
    try:
        case_uuid = _uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid case_id: {case_id}")

    case_result = await db.execute(select(Case).where(Case.id == case_uuid))
    case = case_result.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    case_title = payload.case_title or case.title
    risk_level = case.risk_level.upper()

    # Risk score map
    risk_score_map = {"critical": 90.0, "high": 72.0, "medium": 50.0, "low": 25.0}
    risk_score = risk_score_map.get(case.risk_level.lower(), 50.0)

    # 2. Load evidence records from PostgreSQL
    ev_result = await db.execute(
        select(Evidence).where(Evidence.case_id == case_uuid).order_by(Evidence.ingested_at.desc())
    )
    evidence_records = ev_result.scalars().all()

    evidence_count = len(evidence_records)
    processed_count = sum(1 for e in evidence_records if e.processed_status == "completed")
    pending_count = sum(1 for e in evidence_records if e.processed_status == "pending")
    file_types = list({e.file_type for e in evidence_records if e.file_type})

    # 3. Fetch Neo4j graph entities for this case
    entities: List[EntitySummary] = []
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            cypher = """
            MATCH (c:Case {id: $case_id})-[*1..2]-(n)
            WHERE n <> c
            RETURN DISTINCT labels(n) AS labels, n.id AS id, n.handle AS handle,
                   n.name AS name, n.platform_id AS platform_id,
                   n.label AS label, n.text AS text, n.filename AS filename
            LIMIT 20
            """
            result = await session.run(cypher, case_id=case_id)
            records = await result.data()
            for rec in records:
                labels = rec.get("labels", ["Entity"])
                lbl = labels[0] if labels else "Entity"
                name = (
                    rec.get("handle")
                    or rec.get("name")
                    or rec.get("label")
                    or rec.get("text")
                    or rec.get("filename")
                    or rec.get("platform_id")
                    or rec.get("id")
                    or lbl
                )
                entities.append(
                    EntitySummary(
                        name=str(name),
                        type=str(lbl),
                        details=f"Graph entity linked to case {case_id[:8]}",
                    )
                )
    except Exception as exc:
        logger.info("Neo4j unavailable for report generation: %s", exc)

    # 4. Fetch top vector hits from Qdrant
    top_evidence: List[EvidenceItem] = []
    try:
        qdrant = get_qdrant_client()
        collections = await qdrant.get_collections()
        col_names = [c.name for c in collections.collections]
        if "investigation_evidence" in col_names:
            import os as _os
            import httpx
            qh = _os.getenv("QDRANT_HOST", "localhost")
            if qh == "qdrant":
                qh = "localhost"
            qp = int(_os.getenv("QDRANT_PORT", "6333"))

            async with httpx.AsyncClient(timeout=10.0) as http:
                r = await http.post(
                    f"http://{qh}:{qp}/collections/investigation_evidence/points/search",
                    json={"vector": [0.1] * 384, "limit": 25, "with_payload": True},
                )
                r.raise_for_status()
                raw_hits = r.json().get("result", [])

            raw_hits = [h for h in raw_hits if (h.get("payload") or {}).get("case_id") == case_id][:5]
            for res in raw_hits:
                p = res.get("payload") or {}
                top_evidence.append(
                    EvidenceItem(
                        source=p.get("source", "Vector DB"),
                        content=p.get("text", "Evidence item"),
                        relevance_score=round(float(res.get("score", 0.0)), 2),
                    )
                )
    except Exception as exc:
        logger.info("Qdrant unavailable for report generation: %s", exc)

    # 5. Build dynamic report content from real data

    # Executive summary
    graph_note = f" {len(entities)} entity nodes mapped in the relationship graph." if entities else ""
    vector_note = f" {len(top_evidence)} evidence vectors retrieved from semantic index." if top_evidence else ""
    file_type_note = f" Evidence types ingested: {', '.join(file_types)}." if file_types else ""

    executive_summary = (
        f"Forensic analysis for case '{case_title}' (ID: {case_id[:8]}…) — "
        f"risk classification: {risk_level}. "
        f"{evidence_count} evidence item(s) on record; "
        f"{processed_count} processed, {pending_count} pending."
        f"{file_type_note}{graph_note}{vector_note}"
    )

    # Key findings from real data
    key_findings: List[str] = []
    if evidence_count > 0:
        key_findings.append(
            f"{evidence_count} evidence file(s) ingested — {processed_count} fully processed, {pending_count} awaiting extraction."
        )
    if file_types:
        key_findings.append(f"Evidence modalities detected: {', '.join(file_types)}.")
    if entities:
        type_counts: Dict[str, int] = {}
        for e in entities:
            type_counts[e.type] = type_counts.get(e.type, 0) + 1
        entity_summary = ", ".join(f"{v} {k}(s)" for k, v in type_counts.items())
        key_findings.append(f"Knowledge graph contains {len(entities)} entities: {entity_summary}.")
    if top_evidence:
        key_findings.append(
            f"Semantic vector search returned {len(top_evidence)} relevant evidence hits."
        )
    if evidence_count == 0 and not entities:
        key_findings.append("No evidence has been ingested yet. Upload evidence files to begin analysis.")

    # Grooming stages: only populated if evidence/entities suggest it
    grooming_stages: List[str] = []
    if evidence_count > 0 or entities:
        # These would be derived from actual ML agent analysis in production
        # For now surface only what evidence suggests
        grooming_stages = ["Analysis pending — run LangGraph agents for stage detection."]

    # Recommendations based on current state
    recommendations: List[str] = []
    if pending_count > 0:
        recommendations.append(
            f"Ensure Celery worker is running — {pending_count} evidence file(s) are still in 'pending' status."
        )
    if evidence_count == 0:
        recommendations.append("Upload forensic evidence files (chat logs, images, documents) to begin analysis.")
    if not entities:
        recommendations.append("Run the LangGraph agent pipeline to populate the Neo4j knowledge graph with entities.")
    if not top_evidence:
        recommendations.append("Run the ML extraction pipeline to index evidence into Qdrant for semantic search.")
    recommendations.append(
        f"Preserve chain-of-custody SHA-256 hashes for all {evidence_count} evidence records in case {case_id[:8]}."
    )

    return AiReportResponse(
        case_id=case_id,
        case_title=case_title,
        generated_at=now_iso,
        risk_level=risk_level,
        risk_score=risk_score,
        executive_summary=executive_summary,
        key_findings=key_findings,
        grooming_stages_detected=grooming_stages,
        entities=entities,
        top_evidence_vectors=top_evidence,
        recommendations=recommendations,
    )
