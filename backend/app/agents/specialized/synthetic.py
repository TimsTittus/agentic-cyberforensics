import numpy as np
from typing import Dict, Any, List
from app.agents.state import InvestigationState

def synthetic_agent(state: InvestigationState) -> Dict[str, Any]:
    """LangGraph node function to evaluate metadata anomalies and compute synthetic media probability."""
    raw_payload = state.get("raw_payload", {})
    metadata = raw_payload.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    indicators: List[Dict[str, Any]] = []
    prob_score = 0.1  # baseline probability

    # 1. Missing EXIF device signatures (Make / Model)
    make = metadata.get("Make") or metadata.get("exif_make")
    model = metadata.get("Model") or metadata.get("exif_model")
    software = metadata.get("Software") or metadata.get("exif_software") or ""

    if not make and not model:
        prob_score += 0.35
        indicators.append(
            {
                "type": "Missing Device Signature",
                "description": "No camera Make/Model EXIF tags found; typical of AI-generated media or stripped metadata.",
                "confidence": 0.8,
            }
        )

    # 2. Known GAN / AI Generation Software Signatures
    ai_keywords = ["automatic1111", "comfyui", "midjourney", "stable diffusion", "dall-e", "diffusers", "gan"]
    software_str = str(software).lower()
    if any(kw in software_str for kw in ai_keywords):
        prob_score += 0.5
        indicators.append(
            {
                "type": "AI Generator Signature",
                "description": f"Software EXIF tag indicates AI generator tool: {software}",
                "confidence": 0.95,
            }
        )

    # 3. Explicit synthetic flags in raw payload
    if raw_payload.get("is_synthetic") or raw_payload.get("ai_generated"):
        prob_score += 0.4
        indicators.append(
            {
                "type": "Payload AI Flag",
                "description": "Upstream extraction pipeline flagged payload as AI-generated.",
                "confidence": 0.9,
            }
        )

    # 4. Pixel array variance analysis via numpy if image matrix present
    pixel_data = raw_payload.get("pixel_data")
    if pixel_data is None:
        pixel_data = raw_payload.get("image_array")

    if pixel_data is not None:
        try:
            arr = np.array(pixel_data, dtype=np.float32)
            std_dev = float(np.std(arr))
            if std_dev < 5.0:  # unnaturally low variance
                prob_score += 0.2
                indicators.append(
                    {
                        "type": "Unnatural Pixel Variance",
                        "description": f"Extremely low pixel noise variance (std_dev={std_dev:.2f}).",
                        "confidence": 0.75,
                    }
                )
        except Exception:
            pass

    synthetic_prob = float(min(1.0, round(prob_score, 2)))

    new_media_flags: List[Dict[str, Any]] = []
    if indicators:
        new_media_flags.append(
            {
                "category": "Synthetic Media Detection",
                "synthetic_prob": synthetic_prob,
                "indicators": indicators,
                "deduced_context": f"Synthetic media probability assessed at {synthetic_prob*100:.1f}%.",
                "risk_score": synthetic_prob,
                "confidence": 0.85,
            }
        )

    return {
        "synthetic_prob": synthetic_prob,
        "media_flags": new_media_flags,
    }