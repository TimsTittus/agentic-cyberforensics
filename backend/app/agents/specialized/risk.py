import uuid
import asyncio
import concurrent.futures
from typing import Dict, Any
from sqlalchemy import text
from app.agents.state import InvestigationState
from app.core.database import _async_engine

async def _run_risk_async(state: InvestigationState) -> Dict[str, Any]:
    case_id_str = state.get("case_id", "")
    grooming_flags = state.get("grooming_flags", [])
    media_flags = state.get("media_flags", [])
    synthetic_prob = float(state.get("synthetic_prob", 0.0))
    osint_hits = state.get("osint_hits", [])

    # 1. Component risk assessments
    grooming_risk = max([float(f.get("risk_score", 0.0)) for f in grooming_flags], default=0.0)
    media_risk = max([float(f.get("risk_score", 0.0)) for f in media_flags], default=0.0)
    osint_risk = min(1.0, len(osint_hits) * 0.25)

    # 2. Weighted Victim Risk Matrix calculation
    weighted_score = (
        (grooming_risk * 0.45)
        + (media_risk * 0.25)
        + (synthetic_prob * 0.15)
        + (osint_risk * 0.15)
    )
    final_risk_score = float(round(min(1.0, weighted_score), 2))

    # Determine risk level string for DB constraint ('low', 'medium', 'high', 'critical')
    if final_risk_score >= 0.75:
        risk_level = "critical"
    elif final_risk_score >= 0.50:
        risk_level = "high"
    elif final_risk_score >= 0.25:
        risk_level = "medium"
    else:
        risk_level = "low"

    # 3. Update Postgres `cases` table if engine is connected and case_id is UUID
    if _async_engine is not None:
        try:
            # Check if case_id_str is a valid UUID
            case_uuid = uuid.UUID(case_id_str)
            async with _async_engine.begin() as conn:
                await conn.execute(
                    text("UPDATE cases SET risk_level = :risk_level, updated_at = NOW() WHERE id = :case_id"),
                    {"risk_level": risk_level, "case_id": case_uuid},
                )
        except Exception:
            pass

    return {"risk_score": final_risk_score}

def risk_agent(state: InvestigationState) -> Dict[str, Any]:
    """LangGraph node function to calculate final victim risk matrix and update Postgres cases table."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, _run_risk_async(state)).result()
    else:
        return asyncio.run(_run_risk_async(state))