from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from app.agents.state import InvestigationState
from app.agents.specialized.grooming import grooming_agent
from app.agents.specialized.multimedia import multimedia_agent
from app.agents.specialized.osint import osint_agent
from app.agents.specialized.synthetic import synthetic_agent
from app.agents.specialized.timeline import timeline_agent
from app.agents.specialized.fusion import fusion_agent
from app.agents.specialized.risk import risk_agent

# Entry Gateway node function
def gateway(state: InvestigationState) -> Dict[str, Any]:
    return {}

# Initialize StateGraph
workflow = StateGraph(InvestigationState)

# Add Nodes
workflow.add_node("gateway", gateway)
workflow.add_node("grooming_agent", grooming_agent)
workflow.add_node("multimedia_agent", multimedia_agent)
workflow.add_node("synthetic_agent", synthetic_agent)
workflow.add_node("osint_agent", osint_agent)
workflow.add_node("timeline_agent", timeline_agent)
workflow.add_node("fusion_agent", fusion_agent)
workflow.add_node("risk_agent", risk_agent)

# Set Entry Point: Entry -> gateway
workflow.add_edge(START, "gateway")

# Parallel Routing: gateway -> parallel agents
workflow.add_edge("gateway", "grooming_agent")
workflow.add_edge("gateway", "multimedia_agent")
workflow.add_edge("gateway", "synthetic_agent")
workflow.add_edge("gateway", "osint_agent")

# Sequential Routing: parallel agents -> timeline_agent
workflow.add_edge("grooming_agent", "timeline_agent")
workflow.add_edge("multimedia_agent", "timeline_agent")
workflow.add_edge("synthetic_agent", "timeline_agent")
workflow.add_edge("osint_agent", "timeline_agent")

# Sequential Downstream Routing: timeline_agent -> fusion_agent -> risk_agent -> END
workflow.add_edge("timeline_agent", "fusion_agent")
workflow.add_edge("fusion_agent", "risk_agent")
workflow.add_edge("risk_agent", END)

# Compile Graph
investigation_graph = workflow.compile()

def run_investigation(case_id: str, extraction_artifact: Dict[str, Any]) -> InvestigationState:
    """Trigger the LangGraph investigation workflow for a given case and payload."""
    initial_state: InvestigationState = {
        "case_id": case_id,
        "raw_payload": extraction_artifact or {},
        "extracted_entities": [],
        "grooming_flags": [],
        "osint_hits": [],
        "media_flags": [],
        "synthetic_prob": 0.0,
        "timeline": [],
        "fused_leads": [],
        "risk_score": 0.0,
    }
    return investigation_graph.invoke(initial_state)