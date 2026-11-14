"""
AgentBruce — Evidence Vector Search API

POST /api/v1/search
GET  /api/v1/search

Accepts natural language queries, embeds them using all-MiniLM-L6-v2 (384 dimensions),
and performs vector similarity search in Qdrant across ingested chat logs and OCR texts.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from app.core.database import get_qdrant_client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])

_embedding_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


class SearchRequest(BaseModel):
    query: str
    case_id: Optional[str] = None
    limit: Optional[int] = 5


class SearchHit(BaseModel):
    id: str
    score: float
    text: str
    case_id: str
    source: str


class SearchResponse(BaseModel):
    query: str
    total_hits: int
    hits: List[SearchHit]



@router.post("/search", response_model=SearchResponse, summary="Vector semantic evidence search")
async def search_evidence_post(payload: SearchRequest):
    """Perform vector similarity search against Qdrant collection ``investigation_evidence``."""
    return await _execute_vector_search(payload.query, payload.case_id, payload.limit or 5)


@router.get("/search", response_model=SearchResponse, summary="Vector semantic evidence search GET")
async def search_evidence_get(
    q: str = Query(..., description="Natural language search query"),
    case_id: Optional[str] = Query(None, description="Optional case UUID filter"),
    limit: int = Query(5, description="Max results"),
):
    """GET handler for vector similarity search."""
    return await _execute_vector_search(q, case_id, limit)


async def _execute_vector_search(query: str, case_id: Optional[str], limit: int) -> SearchResponse:
    if not query.strip():
        return SearchResponse(query=query, total_hits=0, hits=[])

    try:
        model = _get_model()
        query_vector = model.encode(query).tolist()

        qdrant = get_qdrant_client()
        collection_name = "investigation_evidence"

        # Check if collection exists
        collections = await qdrant.get_collections()
        collection_names = [c.name for c in collections.collections]

        if collection_name not in collection_names:
            logger.info("Qdrant collection '%s' does not exist yet — no evidence indexed.", collection_name)
            return SearchResponse(query=query, total_hits=0, hits=[])

        # Hit the version-stable REST endpoint directly (works on both the
        # 1.8 server image and the 1.18 client); the client's own search()
        # was removed and query_points() requires Qdrant >= 1.10.
        import os as _os
        import httpx
        qdrant_host = _os.getenv("QDRANT_HOST", "localhost")
        if qdrant_host == "qdrant":
            qdrant_host = "localhost"
        qdrant_port = int(_os.getenv("QDRANT_PORT", "6333"))

        async with httpx.AsyncClient(timeout=10.0) as http:
            r = await http.post(
                f"http://{qdrant_host}:{qdrant_port}/collections/{collection_name}/points/search",
                json={
                    "vector": query_vector,
                    "limit": max(limit, 20),
                    "with_payload": True,
                },
            )
            r.raise_for_status()
            raw = r.json().get("result", [])

        hits: List[SearchHit] = []
        for res in raw:
            payload = res.get("payload") or {}
            if case_id and payload.get("case_id") != case_id:
                continue
            hits.append(
                SearchHit(
                    id=str(res.get("id")),
                    score=round(float(res.get("score", 0.0)), 4),
                    text=payload.get("text", "No text payload"),
                    case_id=payload.get("case_id", case_id or "unknown"),
                    source=payload.get("source", "Qdrant Vector DB"),
                )
            )
            if len(hits) >= limit:
                break

        return SearchResponse(query=query, total_hits=len(hits), hits=hits)

    except Exception as exc:
        logger.warning("Qdrant vector search failed: %s", exc)
        return SearchResponse(query=query, total_hits=0, hits=[])
