import pytest
from app.agents.graph import run_investigation
from app.agents.specialized.grooming import grooming_agent, GroomingIndicator, GroomingAnalysisResult
from app.agents.specialized.multimedia import multimedia_agent, MediaIndicator, MultimediaAnalysisResult

def test_grooming_agent_detects_indicators():
    state = {
        "case_id": "case-grooming-1",
        "raw_payload": {
            "messages": [
                "You are my special friend.",
                "Don't tell your parents about our chat.",
                "Delete this chat right now.",
                "Send a cute photo.",
            ]
        },
        "extracted_entities": [],
        "grooming_flags": [],
        "osint_hits": [],
        "media_flags": [],
        "synthetic_prob": 0.0,
        "timeline": [],
        "fused_leads": [],
        "risk_score": 0.0,
    }

    result = grooming_agent(state)
    assert "grooming_flags" in result
    flags = result["grooming_flags"]
    assert len(flags) > 0
    phases = {f["phase"] for f in flags}
    assert "Trust" in phases or "Isolation" in phases or "Secrecy" in phases or "Sexualization" in phases

def test_multimedia_agent_deduces_context():
    state = {
        "case_id": "case-media-1",
        "raw_payload": {
            "objects": [{"label": "school uniform"}, {"label": "backpack"}],
            "ocr_text": ["Bus Stop", "School Zone"],
        },
        "extracted_entities": [],
        "grooming_flags": [],
        "osint_hits": [],
        "media_flags": [],
        "synthetic_prob": 0.0,
        "timeline": [],
        "fused_leads": [],
        "risk_score": 0.0,
    }

    result = multimedia_agent(state)
    assert "media_flags" in result
    flags = result["media_flags"]
    assert len(flags) > 0
    assert "deduced_context" in flags[0]
    assert "school" in flags[0]["deduced_context"].lower() or "transit" in flags[0]["deduced_context"].lower()

def test_full_graph_with_specialized_agents():
    payload = {
        "messages": [
            "You can trust me, keep this just between us.",
            "Delete the messages.",
        ],
        "objects": [{"label": "school uniform"}],
        "ocr_text": ["Bus Stop"],
    }

    final_state = run_investigation("case-full-pipeline", payload)

    assert len(final_state["grooming_flags"]) > 0
    assert len(final_state["media_flags"]) > 0
    assert isinstance(final_state["grooming_flags"], list)
    assert isinstance(final_state["media_flags"], list)