from datetime import datetime, timezone
from typing import Dict, Any, List
from app.agents.state import InvestigationState

def _parse_timestamp(ts_val: Any, default_idx: int) -> float:
    """Parse various timestamp formats into POSIX float timestamp."""
    if isinstance(ts_val, (int, float)):
        return float(ts_val)
    if isinstance(ts_val, str) and ts_val.strip():
        try:
            dt = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
            return dt.timestamp()
        except ValueError:
            pass
    # Baseline timestamp fallback with sequential offset
    return datetime.now(timezone.utc).timestamp() + (default_idx * 0.001)

def timeline_agent(state: InvestigationState) -> Dict[str, Any]:
    """LangGraph node function to aggregate and sort all state indicators chronologically."""
    raw_payload = state.get("raw_payload", {})
    indicators: List[Dict[str, Any]] = []
    idx = 0

    # 1. Chat messages from raw payload
    if "messages" in raw_payload and isinstance(raw_payload["messages"], list):
        for msg in raw_payload["messages"]:
            if isinstance(msg, dict):
                indicators.append(
                    {
                        "event_type": "chat_message",
                        "timestamp": msg.get("timestamp"),
                        "content": msg.get("content") or msg.get("text"),
                        "sender": msg.get("sender") or msg.get("user") or "Unknown",
                    }
                )
                idx += 1
            else:
                indicators.append(
                    {
                        "event_type": "chat_message",
                        "timestamp": None,
                        "content": str(msg),
                        "sender": "Unknown",
                    }
                )
                idx += 1

    # 2. Grooming Flags
    for flag in state.get("grooming_flags", []):
        item = dict(flag)
        item["event_type"] = "grooming_indicator"
        indicators.append(item)
        idx += 1

    # 3. Multimedia Flags
    for flag in state.get("media_flags", []):
        item = dict(flag)
        item["event_type"] = "media_indicator"
        indicators.append(item)
        idx += 1

    # 4. OSINT Hits
    for hit in state.get("osint_hits", []):
        item = dict(hit)
        item["event_type"] = "osint_hit"
        indicators.append(item)
        idx += 1

    # Sort chronologically based on parsed timestamp
    sorted_timeline = sorted(
        indicators,
        key=lambda item: _parse_timestamp(item.get("timestamp"), idx),
    )

    return {"timeline": sorted_timeline}