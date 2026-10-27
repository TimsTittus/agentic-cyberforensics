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

        # Search Qdrant
        results = await qdrant.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
        )

        hits: List[SearchHit] = []
        for res in results:
            payload = res.payload or {}
            # Filter by case_id if provided
            if case_id and payload.get("case_id") != case_id:
                continue
            hits.append(
                SearchHit(
                    id=str(res.id),
                    score=round(float(res.score), 4),
                    text=payload.get("text", "No text payload"),
                    case_id=payload.get("case_id", case_id or "unknown"),
                    source=payload.get("source", "Qdrant Vector DB"),
                )
            )

        return SearchResponse(query=query, total_hits=len(hits), hits=hits)

    except Exception as exc:
        logger.warning("Qdrant vector search failed: %s", exc)
        return SearchResponse(query=query, total_hits=0, hits=[])
