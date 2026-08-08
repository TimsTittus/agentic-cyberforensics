"""
AgentBruce — Cross-Case Serial Network Engine

Global multi-case graph traversal (Neo4j) and vector similarity matching
(Qdrant) to detect cross-jurisdictional serial offender patterns.

This module bypasses case-level isolation constraints to find entity
overlaps across all case namespaces.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List

from app.agents.state import InvestigationState
from app.core.database import get_neo4j_driver, get_qdrant_client

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# 1. Neo4j Global Graph Matching
# ──────────────────────────────────────────────────────────────────────────

async def find_global_graph_matches(
    case_id: str,
    entity_ids: List[Dict[str, str]],
) -> List[Dict[str, Any]]:
    """
    Search Neo4j across *all* case namespaces for shared entities.

    ``entity_ids`` is a list of dicts like::

        [
            {"type": "Account", "key": "platform_id", "value": "acc-phantom_x"},
            {"type": "Location", "key": "name", "value": "Bus Stop Line 4"},
        ]

    Returns a list of raw match dicts (not yet CrossCaseMatchAlert).
    """
    matches: List[Dict[str, Any]] = []
    try:
        driver = get_neo4j_driver()
    except Exception:
        logger.debug("Neo4j driver unavailable for cross-case scan.")
        return matches

    async with driver.session() as session:
        for entity in entity_ids:
            etype = entity["type"]
            key = entity["key"]
            value = entity["value"]

            # Find any Case linked (within 3 hops) to a node with the
            # same property value, excluding the current case.
            cypher = """
            MATCH (target_node {%s: $value})-[*1..3]-(other_case:Case)
            WHERE other_case.id <> $case_id
            RETURN DISTINCT
                other_case.id    AS matched_case_id,
                other_case.title AS matched_case_title,
                $etype           AS entity_type,
                $value           AS entity_value
            LIMIT 5
            """ % key  # key is an internal property name, safe for interpolation

            try:
                result = await session.run(
                    cypher,
                    value=value,
                    case_id=case_id,
                    etype=etype,
                )
                records = [rec async for rec in result]
                for rec in records:
                    matches.append({
                        "matched_case_id": rec["matched_case_id"],
                        "matched_case_title": rec["matched_case_title"] or f"Case {rec['matched_case_id'][:8]}",
                        "entity_type": rec["entity_type"],
                        "entity_value": rec["entity_value"],
                        "confidence": 0.92,
                        "source": "neo4j_graph",
                    })
            except Exception as exc:
                logger.warning("Cross-case Cypher query failed for %s=%s: %s", key, value, exc)

    return matches


# ──────────────────────────────────────────────────────────────────────────
# 2. Qdrant Global Vector Matching
# ──────────────────────────────────────────────────────────────────────────

async def find_global_vector_matches(
    case_id: str,
    embedding_vector: List[float],
    threshold: float = 0.85,
) -> List[Dict[str, Any]]:
    """
    Query the ``investigation_evidence`` Qdrant collection *without*
    a case_id payload filter, returning high-similarity matches from
    *other* cases.
    """
    matches: List[Dict[str, Any]] = []
    try:
        qdrant = get_qdrant_client()
        collections = await qdrant.get_collections()
        col_names = [c.name for c in collections.collections]
        if "investigation_evidence" not in col_names:
            return matches

        results = await qdrant.search(
            collection_name="investigation_evidence",
            query_vector=embedding_vector,
            limit=10,
        )

        for hit in results:
            payload = hit.payload or {}
            hit_case = payload.get("case_id", "")
            if hit_case and hit_case != case_id and hit.score >= threshold:
                matches.append({
                    "matched_case_id": hit_case,
                    "matched_case_title": f"Case {hit_case[:8]}",
                    "entity_type": "VectorSimilarity",
                    "entity_value": (payload.get("text", "")[:120] or "Embedded evidence"),
                    "confidence": round(float(hit.score), 3),
                    "source": "qdrant_vector",
                })
    except Exception as exc:
        logger.debug("Qdrant cross-case vector search unavailable: %s", exc)

    return matches


# ──────────────────────────────────────────────────────────────────────────
# 3. Orchestrator — called from fusion_agent
# ──────────────────────────────────────────────────────────────────────────

async def run_cross_case_scan(state: InvestigationState) -> List[Dict[str, Any]]:
    """
    Run both graph and vector cross-case matchers.

    1. Collects entity descriptors from the current case's Neo4j subgraph.
    2. Runs ``find_global_graph_matches``.
    3. Builds an embedding from the first chat message and runs
       ``find_global_vector_matches``.
    4. Writes ``[:CROSS_CASE_LINK]`` relationships in Neo4j for each hit.
    5. Returns a list of ``CrossCaseMatchAlert``-shaped dicts.
    """
    case_id = state.get("case_id", "")
    alerts: List[Dict[str, Any]] = []

    # ── Collect entity descriptors from Neo4j ──
    entity_ids: List[Dict[str, str]] = []
    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            cypher = """
            MATCH (c:Case {id: $case_id})-[*1..2]-(n)
            WHERE NOT n:Case
            RETURN DISTINCT labels(n) AS labels, properties(n) AS props
            """
            result = await session.run(cypher, case_id=case_id)
            records = [rec async for rec in result]
            for rec in records:
                labels = rec["labels"]
                props = rec["props"] or {}
                label = labels[0] if labels else "Node"

                # Map node types to their identifying property
                key_map = {
                    "Account": "platform_id",
                    "Device": "device_id",
                    "IPAddress": "ip",
                    "Location": "name",
                    "CameraSerial": "serial_no",
                    "Suspect": "handle",
                }
                prop_key = key_map.get(label)
                if prop_key and props.get(prop_key):
                    entity_ids.append({
                        "type": label,
                        "key": prop_key,
                        "value": str(props[prop_key]),
                    })
    except Exception as exc:
        logger.debug("Could not collect entities for cross-case scan: %s", exc)

    # ── Graph matching ──
    graph_matches = await find_global_graph_matches(case_id, entity_ids)

    # ── Vector matching ──
    vector_matches: List[Dict[str, Any]] = []
    raw_payload = state.get("raw_payload", {})
    texts: List[str] = []
    if "messages" in raw_payload and isinstance(raw_payload["messages"], list):
        for msg in raw_payload["messages"]:
            if isinstance(msg, dict):
                content = msg.get("content") or msg.get("text")
                if content:
                    texts.append(str(content))
            elif isinstance(msg, str) and msg.strip():
                texts.append(msg.strip())
    if "text" in raw_payload and isinstance(raw_payload["text"], str):
        texts.append(raw_payload["text"])

    if texts:
        try:
            from app.agents.specialized.fusion import _get_embedding_model
            model = _get_embedding_model()
            embedding = model.encode(texts[0]).tolist()
            vector_matches = await find_global_vector_matches(case_id, embedding)
        except Exception as exc:
            logger.debug("Vector cross-case matching failed: %s", exc)

    # ── Merge results and deduplicate ──
    all_matches = graph_matches + vector_matches
    seen_keys: set = set()
    for m in all_matches:
        dedup_key = f"{m['matched_case_id']}:{m['entity_type']}:{m['entity_value']}"
        if dedup_key in seen_keys:
            continue
        seen_keys.add(dedup_key)

        alert = {
            "alert_id": str(uuid.uuid4()),
            "current_case_id": case_id,
            "matched_case_id": m["matched_case_id"],
            "matched_case_title": m["matched_case_title"],
            "matched_entity_type": m["entity_type"],
            "matched_entity_value": m["entity_value"],
            "confidence_score": m["confidence"],
            "linking_reason": (
                f"Cross-case {m['source'].replace('_', ' ')} match: "
                f"{m['entity_type']} '{m['entity_value']}' also found in "
                f"case '{m['matched_case_title']}'."
            ),
        }
        alerts.append(alert)

    # ── Write CROSS_CASE_LINK relationships ──
    if alerts:
        try:
            driver = get_neo4j_driver()
            async with driver.session() as session:
                for alert in alerts:
                    link_cypher = """
                    MATCH (c1:Case {id: $current_id})
                    MATCH (c2:Case {id: $matched_id})
                    MERGE (c1)-[r:CROSS_CASE_LINK]->(c2)
                    SET r.timestamp = datetime(),
                        r.confidence_score = $confidence,
                        r.match_type = $match_type
                    """
                    await session.run(
                        link_cypher,
                        current_id=alert["current_case_id"],
                        matched_id=alert["matched_case_id"],
                        confidence=alert["confidence_score"],
                        match_type=alert["matched_entity_type"],
                    )
                logger.info(
                    "Wrote %d CROSS_CASE_LINK relationships for case %s",
                    len(alerts), case_id,
                )
        except Exception as exc:
            logger.warning("Failed to write CROSS_CASE_LINK edges: %s", exc)

    return alerts
