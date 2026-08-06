from typing import TypedDict, List, Dict, Any

class InvestigationState(TypedDict):
    case_id: str
    raw_payload: Dict[str, Any]
    extracted_entities: List[Dict[str, Any]]
    grooming_flags: List[Dict[str, Any]]
    osint_hits: List[Dict[str, Any]]
    media_flags: List[Dict[str, Any]]
    synthetic_prob: float
    timeline: List[Dict[str, Any]]
    fused_leads: List[Dict[str, Any]]
    risk_score: float