import os
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.agents.state import InvestigationState

class GroomingIndicator(BaseModel):
    phase: str = Field(
        description="Grooming phase identified: Trust, Isolation, Secrecy, Sexualization, or Coercion"
    )
    snippet: str = Field(description="Direct text quote or evidence description from the transcript")
    reasoning: str = Field(description="Detailed behavioral analysis explaining the phase transition")
    risk_score: float = Field(description="Risk score from 0.0 (low) to 1.0 (critical)")
    confidence: float = Field(description="Confidence level from 0.0 to 1.0")

class GroomingAnalysisResult(BaseModel):
    indicators: List[GroomingIndicator] = Field(
        default_factory=list, description="List of detected grooming phase indicators"
    )
    overall_risk_score: float = Field(default=0.0, description="Overall risk score from 0.0 to 1.0")
    confidence: float = Field(default=0.0, description="Overall confidence level from 0.0 to 1.0")

GROOMING_SYSTEM_PROMPT = """You are an expert forensic child safety and behavioral analysis AI agent.
Analyze the provided chat transcript to detect grooming behavioral state-transitions.

Do NOT rely on simple keyword matching or adolescent slang in isolation. Instead, evaluate the psychological progression across 5 distinct grooming phases:
1. Trust (Building rapport, flattery, gifts, special attention)
2. Isolation (Driving wedges between victim and parents/friends, demanding exclusive relationship)
3. Secrecy (Instructing victim to delete chats, keep secrets, use private channels)
4. Sexualization (Inappropriate topics, boundary pushing, requesting explicit material)
5. Coercion (Emotional blackmail, threats, pressure, extortion)

Return your findings in the requested structured schema.
"""

def _extract_chat_messages(raw_payload: Dict[str, Any]) -> List[str]:
    """Extract list of chat messages from raw payload, taking the last 20 messages as sliding window."""
    messages = []
    if "messages" in raw_payload and isinstance(raw_payload["messages"], list):
        messages = raw_payload["messages"]
    elif "chat_transcript" in raw_payload and isinstance(raw_payload["chat_transcript"], list):
        messages = raw_payload["chat_transcript"]
    elif "text" in raw_payload:
        text_val = raw_payload["text"]
        if isinstance(text_val, list):
            messages = text_val
        elif isinstance(text_val, str):
            messages = [line.strip() for line in text_val.split("\n") if line.strip()]
    elif "extracted_text" in raw_payload:
        et = raw_payload["extracted_text"]
        if isinstance(et, list):
            messages = et
        elif isinstance(et, str):
            messages = [line.strip() for line in et.split("\n") if line.strip()]

    # Stringify dict items if needed
    formatted_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            sender = msg.get("sender") or msg.get("user") or "User"
            content = msg.get("content") or msg.get("text") or str(msg)
            formatted_messages.append(f"{sender}: {content}")
        else:
            formatted_messages.append(str(msg))

    # Apply 20-message sliding window
    return formatted_messages[-20:]


def _fallback_grooming_analysis(messages: List[str]) -> GroomingAnalysisResult:
    """Rule-assisted fallback analyzer when OpenAI API key is unavailable or API call fails."""
    indicators: List[GroomingIndicator] = []
    full_text = " ".join(messages).lower()

    # Rule checks for the 5 phases
    phase_patterns = [
        ("Trust", r"\b(you can trust me|best friend|special|gift|secret friend)\b", 0.4),
        ("Isolation", r"\b(don't tell your parents|they don't understand|just between us|keep this away from)\b", 0.7),
        ("Secrecy", r"\b(delete (this|the) (chat|message)|keep (it|this) secret|shh|dont tell anyone)\b", 0.8),
        ("Sexualization", r"\b(send (a|pic|photo)|are you alone|what are you wearing|sexy|cute pic)\b", 0.9),
        ("Coercion", r"\b(if you don't|i will post|i'll share|you owe me|or else)\b", 0.95),
    ]

    for msg in messages:
        msg_lower = msg.lower()
        for phase, pattern, score in phase_patterns:
            if re.search(pattern, msg_lower):
                indicators.append(
                    GroomingIndicator(
                        phase=phase,
                        snippet=msg[:150],
                        reasoning=f"Detected pattern indicative of the {phase} phase in chat window.",
                        risk_score=score,
                        confidence=0.85,
                    )
                )

    max_risk = max([ind.risk_score for ind in indicators], default=0.0)
    avg_conf = sum([ind.confidence for ind in indicators]) / len(indicators) if indicators else 0.0

    return GroomingAnalysisResult(
        indicators=indicators,
        overall_risk_score=max_risk,
        confidence=avg_conf,
    )

def grooming_agent(state: InvestigationState) -> Dict[str, Any]:
    """LangGraph node function to evaluate chat transcripts for grooming behaviors."""
    raw_payload = state.get("raw_payload", {})
    messages = _extract_chat_messages(raw_payload)

    if not messages:
        return {"grooming_flags": []}

    api_key = os.getenv("OPENAI_API_KEY")
    result: Optional[GroomingAnalysisResult] = None

    if api_key:
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, api_key=api_key)
            structured_llm = llm.with_structured_output(GroomingAnalysisResult)
            prompt_content = f"Recent 20 Messages in Transcript:\n" + "\n".join(messages)
            res = structured_llm.invoke(
                [
                    SystemMessage(content=GROOMING_SYSTEM_PROMPT),
                    HumanMessage(content=prompt_content),
                ]
            )
            if isinstance(res, GroomingAnalysisResult):
                result = res
        except Exception:
            result = None

    if result is None:
        result = _fallback_grooming_analysis(messages)

    return {"grooming_flags": [ind.model_dump() for ind in result.indicators]}