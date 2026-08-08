import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://bruce:bruceforensics@localhost:5435/agentbruce")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "bruceforensics")
os.environ.setdefault("QDRANT_HOST", "localhost")
os.environ.setdefault("QDRANT_PORT", "6333")
os.environ.setdefault("REDIS_URL", "redis://localhost:6381/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-12345678901234567890")

import pytest
from fastapi.testclient import TestClient

from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_websocket_investigation_stream(client):
    """Test real-time WebSocket connection and event streaming."""
    with client.websocket_connect("/api/v1/ws/investigation/test-case-123") as websocket:
        # Step 1: Send optional payload
        websocket.send_json({"raw_payload": {"test": "payload"}})

        # Step 2: Receive start event
        start_data = websocket.receive_json()
        assert start_data["event"] == "start"
        assert start_data["case_id"] == "test-case-123"

        # Step 3: Receive step events (may include cross_case_match events)
        step_events = []
        while True:
            msg = websocket.receive_json()
            if msg["event"] == "complete":
                break
            if msg["event"] == "cross_case_match":
                continue  # Phase 10: cross-case alerts are separate events
            assert msg["event"] == "step"
            assert "node" in msg
            step_events.append(msg["node"])

        assert len(step_events) >= 8  # All 8 LangGraph agents executed
        assert "gateway" in step_events
        assert "risk_agent" in step_events

def test_search_evidence_post(client):
    """Test POST /api/v1/search endpoint with natural language query."""
    response = client.post(
        "/api/v1/search",
        json={"query": "school bus stop uniform", "limit": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "school bus stop uniform"
    assert "hits" in data
    assert len(data["hits"]) > 0
    first_hit = data["hits"][0]
    assert "text" in first_hit
    assert "score" in first_hit
    assert first_hit["score"] > 0.0

def test_search_evidence_get(client):
    """Test GET /api/v1/search endpoint."""
    response = client.get("/api/v1/search?q=trust+isolation&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "trust isolation"
    assert len(data["hits"]) <= 2

def test_generate_ai_report(client):
    """Test POST /api/v1/report/generate endpoint."""
    response = client.post(
        "/api/v1/report/generate",
        json={
            "case_id": "550e8400-e29b-41d4-a716-446655440000",
            "case_title": "Operation Nighthawk – Telegram Network",
        },
    )
    assert response.status_code == 200
    report = response.json()
    assert report["case_id"] == "550e8400-e29b-41d4-a716-446655440000"
    assert report["risk_level"] == "CRITICAL"
    assert report["risk_score"] > 80.0
    assert len(report["executive_summary"]) > 50
    assert len(report["key_findings"]) >= 3
    assert len(report["entities"]) >= 3
    assert len(report["recommendations"]) >= 2

def test_get_case_evidence(client):
    """Test GET /api/v1/cases/{case_id}/evidence endpoint."""
    # First, list cases to get a valid case_id
    res_cases = client.get("/api/v1/cases")
    assert res_cases.status_code == 200
    cases = res_cases.json()
    if len(cases) > 0:
        case_id = cases[0]["id"]
        res_ev = client.get(f"/api/v1/cases/{case_id}/evidence")
        assert res_ev.status_code == 200
        assert isinstance(res_ev.json(), list)
