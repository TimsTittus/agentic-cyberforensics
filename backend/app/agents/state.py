import operator
from typing import TypedDict, List, Dict, Any, Annotated

class InvestigationState(TypedDict):
    case_id: str
    raw_payload: Dict[str, Any]
    extracted_entities: Annotated[List[Dict[str, Any]], operator.add]
    grooming_flags: Annotated[List[Dict[str, Any]], operator.add]
    osint_hits: Annotated[List[Dict[str, Any]], operator.add]
    media_flags: Annotated[List[Dict[str, Any]], operator.add]
    synthetic_prob: float
    timeline: Annotated[List[Dict[str, Any]], operator.add]
    fused_leads: Annotated[List[Dict[str, Any]], operator.add]
    risk_score: float
    cross_case_alerts: Annotated[List[Dict[str, Any]], operator.add]