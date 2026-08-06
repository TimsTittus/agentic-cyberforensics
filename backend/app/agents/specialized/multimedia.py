import os
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.agents.state import InvestigationState

class MediaIndicator(BaseModel):
    category: str = Field(
        description="Category of context deduced, e.g. Environmental, Geographical, Institutional, Behavioral"
    )
    detected_objects: List[str] = Field(
        default_factory=list, description="YOLO detected object labels associated with this finding"
    )
    detected_text: List[str] = Field(
        default_factory=list, description="EasyOCR text items associated with this finding"
    )
    deduced_context: str = Field(
        description="Inferred environmental or geographical context (e.g., School uniform matched with Bus Stop sign indicates near school transit zone)"
    )
    risk_score: float = Field(description="Assessed risk score from 0.0 (low) to 1.0 (critical)")
    confidence: float = Field(description="Confidence level from 0.0 to 1.0")

class MultimediaAnalysisResult(BaseModel):
    indicators: List[MediaIndicator] = Field(
        default_factory=list, description="List of deduced multimedia intelligence indicators"
    )
    overall_risk_score: float = Field(default=0.0, description="Overall risk score from 0.0 to 1.0")
    confidence: float = Field(default=0.0, description="Overall confidence level from 0.0 to 1.0")

MULTIMEDIA_SYSTEM_PROMPT = """You are an expert digital forensics and intelligence analysis AI agent.
Analyze object detections (YOLO) and extracted text (EasyOCR) from multimedia evidence payloads to deduce geographical and environmental context.

Look for contextual intersections between visual objects and OCR text overlay (e.g., matching a 'school uniform' object with 'Bus Stop' or street sign text, or identifying sensitive location indicators).

Return your findings in the requested structured schema.
"""

def _extract_media_elements(raw_payload: Dict[str, Any]) -> tuple[List[str], List[str]]:
    """Extract detected objects and OCR text from raw evidence payload."""
    detected_objects: List[str] = []
    detected_text: List[str] = []

    # Check for direct or nested keys
    for obj_key in ["objects", "detected_objects", "yolo_objects", "vision_objects"]:
        if obj_key in raw_payload and isinstance(raw_payload[obj_key], list):
            for item in raw_payload[obj_key]:
                if isinstance(item, dict):
                    name = item.get("label") or item.get("class") or item.get("name")
                    if name:
                        detected_objects.append(str(name))
                else:
                    detected_objects.append(str(item))

    for txt_key in ["ocr_text", "easyocr_text", "text", "detected_text"]:
        if txt_key in raw_payload:
            val = raw_payload[txt_key]
            if isinstance(val, list):
                detected_text.extend([str(v) for v in val if v])
            elif isinstance(val, str) and val.strip():
                detected_text.append(val.strip())

    # Check vision extractor nested structure if present
    if "vision" in raw_payload and isinstance(raw_payload["vision"], dict):
        v_dict = raw_payload["vision"]
        if "objects" in v_dict and isinstance(v_dict["objects"], list):
            for item in v_dict["objects"]:
                if isinstance(item, dict):
                    name = item.get("label") or item.get("class") or item.get("name")
                    if name:
                        detected_objects.append(str(name))
                else:
                    detected_objects.append(str(item))
        if "ocr" in v_dict and isinstance(v_dict["ocr"], list):
            detected_text.extend([str(t) for t in v_dict["ocr"] if t])

    return list(set(detected_objects)), list(set(detected_text))

def _fallback_multimedia_analysis(
    detected_objects: List[str], detected_text: List[str]
) -> MultimediaAnalysisResult:
    """Rule-assisted fallback analyzer when OpenAI API key is unavailable or API call fails."""
    indicators: List[MediaIndicator] = []

    objs_lower = [o.lower() for o in detected_objects]
    txt_lower = " ".join([t.lower() for t in detected_text])

    # Deduce school / transit context
    if any(s in objs_lower for s in ["backpack", "school uniform", "child", "person", "tie"]) and any(
        t in txt_lower for t in ["bus stop", "school", "stop", "school zone", "lane"]
    ):
        indicators.append(
            MediaIndicator(
                category="Environmental / Institutional",
                detected_objects=detected_objects,
                detected_text=detected_text,
                deduced_context="School uniform or child-associated items matched with transit/school sign text indicates a school commute zone.",
                risk_score=0.75,
                confidence=0.88,
            )
        )
    elif detected_objects or detected_text:
        indicators.append(
            MediaIndicator(
                category="General Visual Context",
                detected_objects=detected_objects,
                detected_text=detected_text,
                deduced_context=f"Detected objects ({', '.join(detected_objects)}) and OCR text ({', '.join(detected_text)}).",
                risk_score=0.3,
                confidence=0.7,
            )
        )

    max_risk = max([ind.risk_score for ind in indicators], default=0.0)
    avg_conf = sum([ind.confidence for ind in indicators]) / len(indicators) if indicators else 0.0

    return MultimediaAnalysisResult(
        indicators=indicators,
        overall_risk_score=max_risk,
        confidence=avg_conf,
    )

def multimedia_agent(state: InvestigationState) -> Dict[str, Any]:
    """LangGraph node function to evaluate multimedia objects and OCR text."""
    raw_payload = state.get("raw_payload", {})
    detected_objects, detected_text = _extract_media_elements(raw_payload)

    if not detected_objects and not detected_text:
        return {"media_flags": []}

    api_key = os.getenv("OPENAI_API_KEY")
    result: Optional[MultimediaAnalysisResult] = None

    if api_key:
        try:
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0, api_key=api_key)
            structured_llm = llm.with_structured_output(MultimediaAnalysisResult)
            prompt_content = (
                f"YOLO Detected Objects: {', '.join(detected_objects) if detected_objects else 'None'}\n"
                f"EasyOCR Extracted Text: {', '.join(detected_text) if detected_text else 'None'}"
            )
            res = structured_llm.invoke(
                [
                    SystemMessage(content=MULTIMEDIA_SYSTEM_PROMPT),
                    HumanMessage(content=prompt_content),
                ]
            )
            if isinstance(res, MultimediaAnalysisResult):
                result = res
        except Exception:
            result = None

    if result is None:
        result = _fallback_multimedia_analysis(detected_objects, detected_text)

    return {"media_flags": [ind.model_dump() for ind in result.indicators]}