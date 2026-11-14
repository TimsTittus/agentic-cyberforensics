"""
AgentBruce — Celery Worker Tasks

Background tasks executed by Celery workers outside the FastAPI
async event loop.  All database access uses synchronous psycopg2
connections since Celery workers are sync processes.
"""

from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from app.core.celery_app import celery_app
from app.workers.extractors import process_file

logger = logging.getLogger(__name__)

QDRANT_COLLECTION = "investigation_evidence"
EMBEDDING_DIM = 384


def _get_sync_dsn() -> str:
    """
    Convert the async DATABASE_URL to a synchronous psycopg2 DSN.

    The env var uses ``postgresql+asyncpg://…`` for SQLAlchemy async,
    but Celery workers need plain ``postgresql://…`` for psycopg2.
    Falls back to localhost:5435 when running outside the docker network.
    """
    url = os.getenv("DATABASE_URL", "postgresql://bruce:bruceforensics@localhost:5435/agentbruce")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    if "@postgres:5432" in url or "@postgres:" in url:
        url = url.replace("@postgres:5432", "@localhost:5435").replace("@postgres:", "@localhost:5435")
    return url


def _get_neo4j_endpoint() -> tuple[str, str, str]:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    if "neo4j:7687" in uri:
        uri = "bolt://localhost:7687"
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "bruceforensics")
    return uri, user, password


def _get_qdrant_endpoint() -> tuple[str, int]:
    host = os.getenv("QDRANT_HOST", "localhost")
    if host == "qdrant":
        host = "localhost"
    port = int(os.getenv("QDRANT_PORT", "6333"))
    return host, port


_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers all-MiniLM-L6-v2 model...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def _chunk_text(text: str, max_chars: int = 400) -> List[str]:
    """Split text into roughly sentence-sized chunks for embedding."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    for sentence in text.replace("\n", " ").split(". "):
        sentence = sentence.strip()
        if not sentence:
            continue
        if current_len + len(sentence) > max_chars and current:
            chunks.append(". ".join(current).strip())
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence) + 2
    if current:
        chunks.append(". ".join(current).strip())
    return chunks


def _index_to_qdrant(
    evidence_id: str,
    case_id: str,
    file_name: str,
    text_content: str,
    ocr_snippets: List[str],
) -> int:
    """Embed extracted text and upsert into Qdrant. Returns number of points written."""
    host, port = _get_qdrant_endpoint()

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http.models import (
            Distance,
            PointStruct,
            VectorParams,
        )
    except Exception as exc:
        logger.warning("qdrant_client unavailable: %s", exc)
        return 0

    try:
        client = QdrantClient(host=host, port=port, timeout=30)
    except Exception as exc:
        logger.warning("Qdrant connection failed at %s:%s — %s", host, port, exc)
        return 0

    try:
        existing = {c.name for c in client.get_collections().collections}
        if QDRANT_COLLECTION not in existing:
            client.create_collection(
                collection_name=QDRANT_COLLECTION,
                vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection '%s'", QDRANT_COLLECTION)
    except Exception as exc:
        logger.warning("Failed to ensure Qdrant collection: %s", exc)
        return 0

    chunks: List[tuple[str, str]] = []
    for ch in _chunk_text(text_content):
        chunks.append((ch, "OCR Text" if ocr_snippets else "Extracted Text"))
    for snippet in ocr_snippets:
        snippet = snippet.strip()
        if snippet and len(snippet) > 2:
            chunks.append((snippet, "OCR Snippet"))

    if not chunks:
        return 0

    model = _get_embedding_model()
    texts = [c[0] for c in chunks]
    try:
        vectors = model.encode(texts, show_progress_bar=False).tolist()
    except Exception as exc:
        logger.error("Embedding failed: %s", exc)
        return 0

    points = []
    for idx, ((text, source), vec) in enumerate(zip(chunks, vectors)):
        point_id_hex = hashlib.md5(f"{evidence_id}:{idx}:{text}".encode()).hexdigest()
        point_id = int(point_id_hex[:15], 16)
        points.append(
            PointStruct(
                id=point_id,
                vector=vec,
                payload={
                    "evidence_id": evidence_id,
                    "case_id": case_id,
                    "file_name": file_name,
                    "text": text,
                    "source": source,
                },
            )
        )

    try:
        client.upsert(collection_name=QDRANT_COLLECTION, points=points, wait=True)
        logger.info("Qdrant upsert: %d points for evidence %s", len(points), evidence_id)
        return len(points)
    except Exception as exc:
        logger.error("Qdrant upsert failed: %s", exc)
        return 0


def _write_graph_entities(
    evidence_id: str,
    case_id: str,
    file_name: str,
    sha256: str,
    file_type: Optional[str],
    artifact: Dict[str, Any],
) -> int:
    """
    Write extracted entities into Neo4j, linked to the Case + Evidence node.

    Creates:
      - :Evidence node (with filename, sha256, type)
      - :Case–[:HAS_EVIDENCE]–>:Evidence
      - :DetectedObject nodes (deduped per label) for each YOLO label with conf ≥ 0.35
      - :Location node when EXIF GPS present
      - :TextSnippet nodes for salient OCR phrases
    """
    uri, user, password = _get_neo4j_endpoint()

    try:
        from neo4j import GraphDatabase
    except Exception as exc:
        logger.warning("neo4j driver not importable: %s", exc)
        return 0

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
    except Exception as exc:
        logger.warning("Neo4j connection failed at %s — %s", uri, exc)
        return 0

    entity_count = 0
    try:
        with driver.session() as session:
            # Ensure Case + Evidence nodes exist
            session.run(
                """
                MERGE (c:Case {id: $case_id})
                MERGE (e:Evidence {id: $ev_id})
                SET e.filename = $filename,
                    e.sha256 = $sha256,
                    e.file_type = $file_type
                MERGE (c)-[:HAS_EVIDENCE]->(e)
                """,
                case_id=case_id,
                ev_id=evidence_id,
                filename=file_name,
                sha256=sha256,
                file_type=file_type or "binary",
            )
            entity_count += 1

            # Detected objects (dedupe by label, use highest conf)
            objects = artifact.get("objects", []) or []
            best_by_label: Dict[str, float] = {}
            for obj in objects:
                label = (obj.get("label") or "").strip()
                conf = float(obj.get("confidence", 0.0))
                if not label or conf < 0.35:
                    continue
                if conf > best_by_label.get(label, 0.0):
                    best_by_label[label] = conf

            for label, conf in best_by_label.items():
                session.run(
                    """
                    MATCH (e:Evidence {id: $ev_id})
                    MERGE (o:DetectedObject {case_id: $case_id, label: $label})
                    SET o.confidence = $conf
                    MERGE (e)-[:DEPICTS]->(o)
                    """,
                    ev_id=evidence_id,
                    case_id=case_id,
                    label=label,
                    conf=round(conf, 3),
                )
                entity_count += 1

            # GPS location from EXIF metadata
            metadata = artifact.get("metadata", {}) or {}
            exif = metadata.get("exif", {}) or {}
            gps = exif.get("gps") if isinstance(exif, dict) else None
            if isinstance(gps, dict) and "latitude" in gps and "longitude" in gps:
                lat = float(gps["latitude"])
                lon = float(gps["longitude"])
                loc_id = f"loc-{lat:.5f}-{lon:.5f}"
                session.run(
                    """
                    MATCH (e:Evidence {id: $ev_id})
                    MERGE (l:Location {id: $loc_id})
                    SET l.latitude = $lat, l.longitude = $lon, l.name = $name
                    MERGE (e)-[:CAPTURED_AT]->(l)
                    """,
                    ev_id=evidence_id,
                    loc_id=loc_id,
                    lat=lat,
                    lon=lon,
                    name=f"{lat:.4f}, {lon:.4f}",
                )
                entity_count += 1

            # Salient OCR text snippets (>= 4 chars, limit top 10 unique)
            text_content = artifact.get("text_content", "") or ""
            snippets = [
                s.strip() for s in text_content.replace("\n", " ").split()
                if len(s.strip()) >= 4
            ]
            seen: set[str] = set()
            unique_snips: List[str] = []
            for s in snippets:
                low = s.lower()
                if low in seen:
                    continue
                seen.add(low)
                unique_snips.append(s)
                if len(unique_snips) >= 10:
                    break

            for snip in unique_snips:
                snip_id = hashlib.md5(f"{case_id}:{snip.lower()}".encode()).hexdigest()
                session.run(
                    """
                    MATCH (e:Evidence {id: $ev_id})
                    MERGE (t:TextSnippet {id: $snip_id})
                    SET t.text = $text, t.case_id = $case_id
                    MERGE (e)-[:MENTIONS]->(t)
                    """,
                    ev_id=evidence_id,
                    snip_id=snip_id,
                    text=snip,
                    case_id=case_id,
                )
                entity_count += 1

    except Exception as exc:
        logger.error("Neo4j write failed: %s", exc)
    finally:
        try:
            driver.close()
        except Exception:
            pass

    logger.info("Neo4j entities written: %d for evidence %s", entity_count, evidence_id)
    return entity_count


@celery_app.task(name="route_evidence", bind=True, max_retries=3)
def route_evidence(self, evidence_id: str) -> dict:
    """
    Transition evidence status to 'processing', execute ML extraction pipeline,
    persist structured JSON results to PostgreSQL, embed text into Qdrant,
    and materialize entities into Neo4j.
    """
    dsn = _get_sync_dsn()

    logger.info("route_evidence started: evidence_id=%s", evidence_id)

    conn = None
    try:
        conn = psycopg2.connect(dsn)
        conn.autocommit = False

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE evidence
                   SET processed_status = 'processing'
                  WHERE id = %s
                    AND processed_status IN ('pending', 'failed')
              RETURNING id, case_id, file_path, file_type, sha256_hash
                """,
                (evidence_id,),
            )
            row = cur.fetchone()

            if row is None:
                conn.rollback()
                logger.warning("Evidence %s not found or already processing.", evidence_id)
                return {
                    "evidence_id": evidence_id,
                    "status": "skipped",
                    "detail": "Record not found or not in 'pending' state.",
                }
            conn.commit()

        file_path = row["file_path"]
        file_type = row.get("file_type")
        case_id = str(row["case_id"])
        sha256 = row["sha256_hash"]
        file_name = os.path.basename(file_path)

        logger.info(
            "Evidence %s transitioned to 'processing'. Executing process_file: path=%s, type=%s",
            evidence_id,
            file_path,
            file_type,
        )

        # 1. Run ML extraction pipeline
        artifact = process_file(file_path=file_path, file_type=file_type)

        # 2. Embed and index text content into Qdrant
        ocr_snippets: List[str] = []
        try:
            raw_text = artifact.get("text_content", "") or ""
            if raw_text:
                ocr_snippets = [
                    line.strip() for line in raw_text.split()
                    if len(line.strip()) >= 3
                ][:40]
        except Exception:
            pass

        qdrant_points = 0
        try:
            qdrant_points = _index_to_qdrant(
                evidence_id=evidence_id,
                case_id=case_id,
                file_name=file_name,
                text_content=artifact.get("text_content", "") or "",
                ocr_snippets=ocr_snippets,
            )
        except Exception as exc:
            logger.error("Qdrant indexing failed for %s: %s", evidence_id, exc)

        # 3. Write entities to Neo4j graph
        neo4j_entities = 0
        try:
            neo4j_entities = _write_graph_entities(
                evidence_id=evidence_id,
                case_id=case_id,
                file_name=file_name,
                sha256=sha256,
                file_type=file_type,
                artifact=artifact,
            )
        except Exception as exc:
            logger.error("Neo4j entity write failed for %s: %s", evidence_id, exc)

        # 4. Enrich artifact with downstream counts, then persist
        artifact["pipeline"] = {
            "qdrant_vectors_indexed": qdrant_points,
            "neo4j_entities_created": neo4j_entities,
        }

        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE evidence
                   SET processed_status = 'completed',
                       extracted_data = %s
                  WHERE id = %s
                """,
                (Json(artifact), evidence_id),
            )
            conn.commit()

        logger.info(
            "Evidence %s completed: %d qdrant points, %d neo4j entities.",
            evidence_id,
            qdrant_points,
            neo4j_entities,
        )

        return {
            "evidence_id": evidence_id,
            "file_path": file_path,
            "status": "completed",
            "qdrant_vectors": qdrant_points,
            "neo4j_entities": neo4j_entities,
        }

    except Exception as exc:
        logger.error("route_evidence failed for %s: %s", evidence_id, exc, exc_info=True)
        if conn is not None:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE evidence
                           SET processed_status = 'failed'
                         WHERE id = %s
                        """,
                        (evidence_id,),
                    )
                    conn.commit()
            except Exception as update_err:
                logger.error("Failed to set status to 'failed' for %s: %s", evidence_id, update_err)

        raise self.retry(exc=exc, countdown=5)

    finally:
        if conn is not None:
            conn.close()
