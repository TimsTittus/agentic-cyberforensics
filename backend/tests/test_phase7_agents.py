import pytest
from app.agents.graph import run_investigation, investigation_graph
from app.agents.specialized.timeline import timeline_agent
from app.agents.specialized.fusion import fusion_agent
from app.agents.specialized.risk import risk_agent

def test_timeline_agent_chronological_sorting():
    state = {
        "case_id": "case-timeline-1",
        "raw_payload": {
            "messages": [
                {"timestamp": "2026-08-01T10:00:00Z", "content": "First message", "sender": "UserA"},
                {"timestamp": "2026-08-01T09:00:00Z", "content": "Earlier message", "sender": "UserB"},
            ]
        },
        "extracted_entities": [],
        "grooming_flags": [{"timestamp": "2026-08-01T11:00:00Z", "phase": "Trust"}],
        "osint_hits": [{"timestamp": "2026-08-01T08:30:00Z", "selector": "ip1"}],
        "media_flags": [],
        "synthetic_prob": 0.0,
        "timeline": [],
        "fused_leads": [],
        "risk_score": 0.0,
        "cross_case_alerts": [],
    }

    result = timeline_agent(state)
    assert "timeline" in result
    timeline = result["timeline"]
    assert len(timeline) == 4
    # Earliest event should be 08:30 OSINT hit
    assert timeline[0]["event_type"] == "osint_hit"
    assert timeline[0]["selector"] == "ip1"
    # Latest event should be 11:00 Grooming flag
    assert timeline[-1]["event_type"] == "grooming_indicator"

def test_fusion_agent_execution():
    state = {
        "case_id": "case-fusion-1",
        "raw_payload": {
            "messages": ["I can help you with your homework."],
            "text": "Extracted OCR document text",
        },
        "extracted_entities": [],
        "grooming_flags": [{"phase": "Trust", "risk_score": 0.5}],
        "osint_hits": [{"type": "username", "selector": "suspect_x"}],
        "media_flags": [{"deduced_context": "School Bus Stop"}],
        "synthetic_prob": 0.2,
        "timeline": [],
        "fused_leads": [],
        "risk_score": 0.0,
        "cross_case_alerts": [],
    }

    result = fusion_agent(state)
    assert "fused_leads" in result
    fused = result["fused_leads"]
    assert len(fused) > 0
    types = {f["type"] for f in fused}
    assert any("Graph" in t for t in types)
    assert any("Vector" in t or "Embedding" in t for t in types)

def test_risk_agent_calculation():
    state = {
        "case_id": "case-risk-1",
        "raw_payload": {},
        "extracted_entities": [],
        "grooming_flags": [{"risk_score": 0.9}],
        "media_flags": [{"risk_score": 0.8}],
        "osint_hits": [{"type": "email", "selector": "e1"}, {"type": "ip", "selector": "ip1"}],
        "synthetic_prob": 0.85,
        "timeline": [],
        "fused_leads": [],
        "risk_score": 0.0,
        "cross_case_alerts": [],
    }

    result = risk_agent(state)
    assert "risk_score" in result
    assert result["risk_score"] >= 0.75  # Critical risk level threshold

def test_complete_end_to_end_langgraph_pipeline():
    payload = {
        "metadata": {
            "email": "suspect@darknet.org",
            "ip": "198.51.100.42",
            "Software": "ComfyUI",
        },
        "messages": [
            {"timestamp": "2026-08-01T10:00:00Z", "sender": "Unknown", "content": "You can trust me."},
            {"timestamp": "2026-08-01T10:05:00Z", "sender": "Unknown", "content": "Don't tell your parents."},
            {"timestamp": "2026-08-01T10:10:00Z", "sender": "Unknown", "content": "Delete this chat."},
        ],
        "objects": [{"label": "backpack"}, {"label": "school uniform"}],
        "ocr_text": ["Bus Stop", "School Zone"],
    }

    case_id = "550e8400-e29b-41d4-a716-446655440000"
    final_state = run_investigation(case_id, payload)

    assert final_state["case_id"] == case_id
    assert len(final_state["grooming_flags"]) >= 1
    assert len(final_state["media_flags"]) >= 1
    assert len(final_state["osint_hits"]) >= 2
    assert final_state["synthetic_prob"] >= 0.8
    assert len(final_state["timeline"]) >= 3
    assert len(final_state["fused_leads"]) >= 1
    assert final_state["risk_score"] > 0.5