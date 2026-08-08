import pytest
from app.agents.state import InvestigationState
from app.agents.graph import investigation_graph, run_investigation

def test_investigation_state_keys():
    state: InvestigationState = {
        "case_id": "test-case-123",
        "raw_payload": {"sample": "data"},
        "extracted_entities": [],
        "grooming_flags": [],
        "osint_hits": [],
        "media_flags": [],
        "synthetic_prob": 0.0,
        "timeline": [],
        "fused_leads": [],
        "risk_score": 0.0,
        "cross_case_alerts": [],
    }
    assert state["case_id"] == "test-case-123"
    assert state["raw_payload"] == {"sample": "data"}
    assert state["risk_score"] == 0.0

def test_run_investigation_execution():
    mock_payload = {"evidence_file": "sample.jpg", "metadata": {"width": 1920}}
    case_id = "case-uuid-999"

    result = run_investigation(case_id, mock_payload)

    assert result["case_id"] == case_id
    assert result["raw_payload"] == mock_payload
    assert isinstance(result["extracted_entities"], list)
    assert isinstance(result["grooming_flags"], list)
    assert isinstance(result["osint_hits"], list)
    assert isinstance(result["media_flags"], list)
    assert isinstance(result["synthetic_prob"], float)
    assert isinstance(result["timeline"], list)
    assert isinstance(result["fused_leads"], list)
    assert isinstance(result["risk_score"], float)

def test_graph_nodes_and_edges():
    nodes = set(investigation_graph.nodes.keys())
    expected_nodes = {
        "gateway",
        "grooming_agent",
        "multimedia_agent",
        "synthetic_agent",
        "osint_agent",
        "timeline_agent",
        "fusion_agent",
        "risk_agent",
    }
    for expected in expected_nodes:
        assert expected in nodes