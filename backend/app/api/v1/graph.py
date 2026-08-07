"""
AgentBruce — Graph Visualization API Endpoint

GET /api/v1/graph — Fetch nodes and edges from Neo4j for force graph visualization.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from neo4j import AsyncDriver

from app.core.database import get_neo4j_driver

logger = logging.getLogger(__name__)

router = APIRouter(tags=["graph"])

NODE_COLOR_MAP = {
    "Case": "#6366f1",
    "Suspect": "#ef4444",
    "Victim": "#f59e0b",
    "Account": "#ec4899",
    "Location": "#22c55e",
    "IPAddress": "#06b6d4",
    "Evidence": "#8b5cf6",
}

@router.get(
    "/graph",
    summary="Fetch intelligence graph nodes and links from Neo4j",
)
async def get_intelligence_graph(
    case_id: Optional[str] = None,
    neo4j: AsyncDriver = Depends(get_neo4j_driver),
):
    """
    Query Neo4j for nodes and relationships.
    Returns JSON formatted for react-force-graph rendering.
    If a case_id is queried but not found in Neo4j, auto-populates Case & Evidence nodes from PostgreSQL.
    """
    import uuid
    import os
    from sqlalchemy import select
    from app.models.schemas import Case as CaseModel, Evidence as EvidenceModel
    from app.core.database import _async_session_factory

    if case_id:
        cypher = """
        MATCH (c:Case {id: $case_id})
        MATCH path = (c)-[*0..3]-(n)
        WITH c, n
        OPTIONAL MATCH (n)-[r]->(m)
        WHERE (c)-[*0..3]-(m)
        RETURN n, r, m
        LIMIT 300
        """
        params = {"case_id": case_id}
    else:
        cypher = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT 200
        """
        params = {}

    nodes_map: Dict[str, Dict[str, Any]] = {}
    links: List[Dict[str, Any]] = []

    try:
        async with neo4j.session() as session:
            result = await session.run(cypher, **params)
            records = [rec async for rec in result]

            # Auto-populate Case and Evidence nodes from PostgreSQL if Neo4j returned nothing for case_id
            if case_id and not records and _async_session_factory:
                try:
                    case_uuid = uuid.UUID(case_id)
                    async with _async_session_factory() as db_session:
                        case_res = await db_session.execute(select(CaseModel).where(CaseModel.id == case_uuid))
                        case_record = case_res.scalar_one_or_none()
                        
                        if case_record:
                            # 1. Populate Case details and default Suspect / Victim
                            seed_cypher = """
                            MERGE (c:Case {id: $case_id})
                            SET c.title = $title, c.status = $status, c.risk_level = $risk_level
                            MERGE (s:Suspect {id: $suspect_id})
                            SET s.handle = "suspect_target"
                            MERGE (v:Victim {id: $victim_id})
                            MERGE (c)-[:INVESTIGATES]->(s)
                            MERGE (c)-[:INVESTIGATES]->(v)
                            """
                            await session.run(
                                seed_cypher,
                                case_id=case_id,
                                title=case_record.title,
                                status=case_record.status,
                                risk_level=case_record.risk_level,
                                suspect_id=f"suspect-{case_id}",
                                victim_id=f"victim-{case_id}",
                            )

                            # 2. Fetch and populate Evidence nodes
                            ev_res = await db_session.execute(select(EvidenceModel).where(EvidenceModel.case_id == case_uuid))
                            evidence_list = ev_res.scalars().all()
                            
                            for ev in evidence_list:
                                filename = os.path.basename(ev.file_path)
                                ev_cypher = """
                                MATCH (c:Case {id: $case_id})
                                MERGE (e:Evidence {id: $ev_id})
                                SET e.filename = $filename, e.file_type = $file_type, e.sha256 = $sha256
                                MERGE (c)-[:HAS_EVIDENCE]->(e)
                                """
                                await session.run(
                                    ev_cypher,
                                    case_id=case_id,
                                    ev_id=str(ev.id),
                                    filename=filename,
                                    file_type=ev.file_type or "binary",
                                    sha256=ev.sha256_hash,
                                )
                            
                            # Re-run graph query after seeding
                            result = await session.run(cypher, **params)
                            records = [rec async for rec in result]
                except Exception as seed_err:
                    logger.warning("Cound not auto-seed graph from PostgreSQL: %s", seed_err)

            for rec in records:
                n = rec.get("n")
                r = rec.get("r")
                m = rec.get("m")

                if n:
                    node_id = str(n.element_id if hasattr(n, "element_id") else n.id if hasattr(n, "id") else n.get("id", str(hash(str(n)))))
                    labels = list(n.labels) if hasattr(n, "labels") else ["Node"]
                    primary_label = labels[0] if labels else "Node"
                    display_name = n.get("filename") or n.get("name") or n.get("handle") or n.get("title") or n.get("id") or primary_label

                    if node_id not in nodes_map:
                        nodes_map[node_id] = {
                            "id": node_id,
                            "label": str(display_name),
                            "type": primary_label,
                            "color": NODE_COLOR_MAP.get(primary_label, "#6366f1"),
                        }

                if m:
                    m_id = str(m.element_id if hasattr(m, "element_id") else m.id if hasattr(m, "id") else m.get("id", str(hash(str(m)))))
                    m_labels = list(m.labels) if hasattr(m, "labels") else ["Node"]
                    m_primary = m_labels[0] if m_labels else "Node"
                    m_display = m.get("filename") or m.get("name") or m.get("handle") or m.get("title") or m.get("id") or m_primary

                    if m_id not in nodes_map:
                        nodes_map[m_id] = {
                            "id": m_id,
                            "label": str(m_display),
                            "type": m_primary,
                            "color": NODE_COLOR_MAP.get(m_primary, "#6366f1"),
                        }

                if n and m and r:
                    n_id = str(n.element_id if hasattr(n, "element_id") else n.id if hasattr(n, "id") else n.get("id", str(hash(str(n)))))
                    m_id = str(m.element_id if hasattr(m, "element_id") else m.id if hasattr(m, "id") else m.get("id", str(hash(str(m)))))
                    rel_type = r.type if hasattr(r, "type") else "RELATED"
                    links.append({
                        "source": n_id,
                        "target": m_id,
                        "label": str(rel_type),
                    })

        return {
            "nodes": list(nodes_map.values()),
            "links": links,
        }

    except Exception as e:
        logger.warning("Failed to query Neo4j graph: %s", e)
        return {
            "nodes": [],
            "links": [],
        }