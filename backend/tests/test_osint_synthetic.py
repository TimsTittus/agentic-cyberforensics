import pytest
import numpy as np
from app.agents.graph import run_investigation
from app.agents.specialized.osint import osint_agent, _run_osint_async, _extract_selectors
from app.agents.specialized.synthetic import synthetic_agent

def test_extract_selectors():
    payload = {
        "metadata": {
            "ip": "192.168.1.1",
            "email": "test@example.com",
            "username": "user123",
        }
    }
    selectors = _extract_selectors(payload)
    assert selectors["ips"] == ["192.168.1.1"]
    assert selectors["emails"] == ["test@example.com"]
    assert selectors["usernames"] == ["user123"]

def test_osint_agent_execution_and_resilience():
    state = {
        "case_id": "case-osint-1",
        "raw_payload": {
            "metadata": {
                "ip": "10.0.0.1",
                "email": "suspect@darknet.org",
                "username": "phantom",
            }
        },
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

    result = osint_agent(state)
    assert "osint_hits" in result
    hits = result["osint_hits"]
    assert len(hits) == 3
    selectors_hit = {h["selector"] for h in hits}
    assert "10.0.0.1" in selectors_hit
    assert "suspect@darknet.org" in selectors_hit
    assert "phantom" in selectors_hit

@pytest.mark.asyncio
async def test_osint_agent_async_direct():
    state = {
        "case_id": "case-osint-async",
        "raw_payload": {
            "metadata": {
                "email": "async_user@test.org",
            }
        },
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

    result = await _run_osint_async(state)
    assert "osint_hits" in result
    assert len(result["osint_hits"]) == 1

def test_synthetic_agent_detects_missing_exif():
    state = {
        "case_id": "case-synthetic-1",
        "raw_payload": {
            "metadata": {
                "Software": "Automatic1111 WebUI",
            }
        },
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

    result = synthetic_agent(state)
    assert "synthetic_prob" in result
    assert result["synthetic_prob"] >= 0.8
    assert "media_flags" in result
    assert len(result["media_flags"]) > 0

def test_synthetic_agent_numpy_pixel_variance():
    flat_image = np.ones((50, 50), dtype=np.float32) * 128.0
    state = {
        "case_id": "case-synthetic-2",
        "raw_payload": {
            "pixel_data": flat_image,
            "metadata": {},
        },
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

    result = synthetic_agent(state)
    assert result["synthetic_prob"] > 0.3

def test_full_graph_parallel_osint_synthetic():
    payload = {
        "metadata": {
            "email": "investigated@domain.com",
            "ip": "172.16.0.5",
            "Software": "Midjourney v5",
        },
        "messages": ["Trust me, keep it secret."],
    }

    final_state = run_investigation("case-phase6-test", payload)

    assert len(final_state["osint_hits"]) >= 2
    assert final_state["synthetic_prob"] >= 0.8
    assert len(final_state["grooming_flags"]) >= 1