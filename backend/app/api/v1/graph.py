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
    "Suspect": "#ef4444",
    "Victim": "#f59e0b",
    "Account": "#6366f1",
    "Location": "#22c55e",
    "IPAddress": "#06b6d4",
    "Evidence": "#ec4899",
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
    """
    cypher = """
    MATCH (n)
    OPTIONAL MATCH (n)-[r]->(m)
    RETURN n, r, m
    LIMIT 200
    """

    nodes_map: Dict[str, Dict[str, Any]] = {}
    links: List[Dict[str, Any]] = []

    try:
        async with neo4j.session() as session:
            result = await session.run(cypher)
            records = await result.data()

            for rec in records:
                n = rec.get("n")
                r = rec.get("r")
                m = rec.get("m")

                if n:
                    node_id = str(n.element_id if hasattr(n, "element_id") else n.get("id", str(hash(str(n)))))
                    labels = list(n.labels) if hasattr(n, "labels") else ["Node"]
                    primary_label = labels[0] if labels else "Node"
                    display_name = n.get("name") or n.get("handle") or n.get("title") or n.get("id") or primary_label

                    if node_id not in nodes_map:
                        nodes_map[node_id] = {
                            "id": node_id,
                            "label": str(display_name),
                            "type": primary_label,
                            "color": NODE_COLOR_MAP.get(primary_label, "#6366f1"),
                        }

                if m:
                    m_id = str(m.element_id if hasattr(m, "element_id") else m.get("id", str(hash(str(m)))))
                    m_labels = list(m.labels) if hasattr(m, "labels") else ["Node"]
                    m_primary = m_labels[0] if m_labels else "Node"
                    m_display = m.get("name") or m.get("handle") or m.get("title") or m.get("id") or m_primary

                    if m_id not in nodes_map:
                        nodes_map[m_id] = {
                            "id": m_id,
                            "label": str(m_display),
                            "type": m_primary,
                            "color": NODE_COLOR_MAP.get(m_primary, "#6366f1"),
                        }

                if n and m and r:
                    n_id = str(n.element_id if hasattr(n, "element_id") else n.get("id", str(hash(str(n)))))
                    m_id = str(m.element_id if hasattr(m, "element_id") else m.get("id", str(hash(str(m)))))
                    rel_type = r[1] if isinstance(r, tuple) else getattr(r, "type", "RELATED")
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