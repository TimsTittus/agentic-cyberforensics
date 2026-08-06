"""
AgentBruce — ML Extraction Pipeline Wrappers

Converts raw forensic media (images, audio/video, documents) into structured
text, objects, and EXIF/file metadata JSON payloads.
"""

from __future__ import annotations

import logging
import mimetypes
import os
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Supported file extensions for routing
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"}
AUDIO_VIDEO_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac",
    ".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"
}


class MetadataExtractor:
    """
    Strips and parses EXIF metadata (GPS coordinates, device model, timestamps)
    and general file attributes from raw files into clean JSON-serializable dicts.
    """

    @staticmethod
    def _convert_to_serializable(val: Any) -> Any:
        """Helper to convert non-JSON serializable EXIF types (bytes, tuples, rationals) to native types."""
        if isinstance(val, (int, float, str, bool)) or val is None:
            return val
        elif isinstance(val, bytes):
            try:
                return val.decode("utf-8", errors="ignore")
            except Exception:
                return str(val)
        elif isinstance(val, tuple):
            return [MetadataExtractor._convert_to_serializable(x) for x in val]
        elif isinstance(val, list):
            return [MetadataExtractor._convert_to_serializable(x) for x in val]
        elif isinstance(val, dict):
            return {str(k): MetadataExtractor._convert_to_serializable(v) for k, v in val.items()}
        elif hasattr(val, "numerator") and hasattr(val, "denominator"):  # IFDRational or Fraction
            try:
                return float(val) if val.denominator != 0 else 0.0
            except Exception:
                return str(val)
        else:
            return str(val)

    @classmethod
    def _parse_gps(cls, gps_info: Dict[int, Any]) -> Dict[str, Any]:
        """Convert GPS EXIF tags to decimal latitude, longitude, and altitude."""
        from PIL.ExifTags import GPSTAGS

        gps_data: Dict[str, Any] = {}
        for tag, val in gps_info.items():
            tag_name = GPSTAGS.get(tag, tag)
            gps_data[tag_name] = cls._convert_to_serializable(val)

        res: Dict[str, Any] = {}

        def _to_decimal(dms: Any, ref: Any) -> Optional[float]:
            if not isinstance(dms, (list, tuple)) or len(dms) < 3:
                return None
            try:
                d = float(dms[0])
                m = float(dms[1])
                s = float(dms[2])
                dec = d + (m / 60.0) + (s / 3600.0)
                if isinstance(ref, str) and ref.upper() in ["S", "W"]:
                    dec = -dec
                return round(dec, 6)
            except Exception:
                return None

        if "GPSLatitude" in gps_data and "GPSLatitudeRef" in gps_data:
            lat = _to_decimal(gps_data["GPSLatitude"], gps_data["GPSLatitudeRef"])
            if lat is not None:
                res["latitude"] = lat

        if "GPSLongitude" in gps_data and "GPSLongitudeRef" in gps_data:
            lon = _to_decimal(gps_data["GPSLongitude"], gps_data["GPSLongitudeRef"])
            if lon is not None:
                res["longitude"] = lon

        if "GPSAltitude" in gps_data:
            try:
                alt = float(gps_data["GPSAltitude"])
                if gps_data.get("GPSAltitudeRef") == 1:
                    alt = -alt
                res["altitude"] = round(alt, 2)
            except Exception:
                pass

        return res

    def extract(self, file_path: str, file_type: Optional[str] = None) -> Dict[str, Any]:
        """Extract general file metadata and EXIF tags from a file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        ext = os.path.splitext(file_path)[1].lower()
        mime, _ = mimetypes.guess_type(file_path)
        mime = mime or file_type or "application/octet-stream"

        metadata: Dict[str, Any] = {
            "file_name": os.path.basename(file_path),
            "file_size_bytes": file_size,
            "extension": ext,
            "mime_type": mime,
            "exif": {},
        }

        # If image, attempt PIL EXIF parsing
        if ext in IMAGE_EXTENSIONS or mime.startswith("image/"):
            try:
                from PIL import Image, ExifTags
                with Image.open(file_path) as img:
                    metadata["dimensions"] = {"width": img.width, "height": img.height}
                    exif_raw = img.getexif()
                    if exif_raw:
                        exif_dict: Dict[str, Any] = {}
                        for tag_id, val in exif_raw.items():
                            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                            if tag_name == "GPSInfo" and isinstance(val, dict):
                                gps_parsed = self._parse_gps(val)
                                if gps_parsed:
                                    exif_dict["gps"] = gps_parsed
                            else:
                                exif_dict[tag_name] = self._convert_to_serializable(val)
                        metadata["exif"] = exif_dict
            except Exception as e:
                logger.warning("Failed to extract EXIF data from %s: %s", file_path, e)

        return metadata


class VisionExtractor:
    """
    Uses YOLOv8 to detect objects (bounding boxes, confidence, class names)
    and EasyOCR to extract text arrays from images.
    """

    def __init__(self, yolo_model_name: str = "yolov8n.pt"):
        self.yolo_model_name = yolo_model_name
        self._yolo_model: Any = None
        self._ocr_reader: Any = None

    @property
    def yolo_model(self) -> Any:
        if self._yolo_model is None:
            from ultralytics import YOLO
            logger.info("Loading YOLO model: %s", self.yolo_model_name)
            self._yolo_model = YOLO(self.yolo_model_name)
        return self._yolo_model

    @property
    def ocr_reader(self) -> Any:
        if self._ocr_reader is None:
            import easyocr
            logger.info("Initializing EasyOCR reader (en)")
            self._ocr_reader = easyocr.Reader(["en"], gpu=False)
        return self._ocr_reader

    def extract(self, image_path: str) -> Dict[str, Any]:
        """Detect objects and perform OCR on an image file."""
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        objects: List[Dict[str, Any]] = []
        text_array: List[str] = []

        # 1. YOLOv8 Object Detection
        try:
            results = self.yolo_model(image_path, verbose=False)
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    xyxy = box.xyxy[0].tolist()
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    class_name = r.names.get(cls_id, str(cls_id))

                    objects.append({
                        "label": class_name,
                        "confidence": round(conf, 4),
                        "box": [round(c, 2) for c in xyxy],
                    })
        except Exception as e:
            logger.error("YOLO object detection failed on %s: %s", image_path, e)

        # 2. EasyOCR Text Extraction
        try:
            ocr_results = self.ocr_reader.readtext(image_path)
            for bbox, text, prob in ocr_results:
                clean_text = str(text).strip()
                if clean_text:
                    text_array.append(clean_text)
        except Exception as e:
            logger.error("EasyOCR extraction failed on %s: %s", image_path, e)

        return {
            "objects": objects,
            "text_array": text_array,
            "text_content": " ".join(text_array),
        }


class AudioExtractor:
    """
    Uses OpenAI Whisper (base model) to transcribe audio/video files
    into text with precise timestamp segments.
    """

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self._model: Any = None

    @property
    def model(self) -> Any:
        if self._model is None:
            import whisper
            logger.info("Loading Whisper model: %s", self.model_name)
            self._model = whisper.load_model(self.model_name)
        return self._model

    def extract(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio/video file and extract timestamped segments."""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            result = self.model.transcribe(audio_path)
            full_text = result.get("text", "").strip()
            raw_segments = result.get("segments", [])

            segments: List[Dict[str, Any]] = []
            for seg in raw_segments:
                segments.append({
                    "start": round(float(seg.get("start", 0.0)), 2),
                    "end": round(float(seg.get("end", 0.0)), 2),
                    "text": str(seg.get("text", "")).strip(),
                })

            return {
                "text_content": full_text,
                "segments": segments,
            }
        except Exception as e:
            logger.error("Whisper transcription failed on %s: %s", audio_path, e)
            return {
                "text_content": "",
                "segments": [],
            }


# Module singletons for reuse
_vision_extractor: Optional[VisionExtractor] = None
_audio_extractor: Optional[AudioExtractor] = None
_metadata_extractor = MetadataExtractor()


def get_vision_extractor() -> VisionExtractor:
    global _vision_extractor
    if _vision_extractor is None:
        _vision_extractor = VisionExtractor()
    return _vision_extractor


def get_audio_extractor() -> AudioExtractor:
    global _audio_extractor
    if _audio_extractor is None:
        _audio_extractor = AudioExtractor()
    return _audio_extractor


def process_file(file_path: str, file_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Central router that inspects a file and routes it to the appropriate
    extractors, returning a standardized JSON artifact payload.

    Standard Payload Schema:
        {
            "text_content": "...",
            "objects": [...],
            "metadata": {...}
        }
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    mime, _ = mimetypes.guess_type(file_path)
    mime = mime or file_type or ""

    # Extract metadata first for all files
    metadata = _metadata_extractor.extract(file_path, file_type=file_type)

    text_content = ""
    objects: List[Dict[str, Any]] = []

    # Route based on file type or extension
    if ext in IMAGE_EXTENSIONS or mime.startswith("image/"):
        logger.info("Processing image evidence: %s", file_path)
        vision_ext = get_vision_extractor()
        vision_res = vision_ext.extract(file_path)
        text_content = vision_res.get("text_content", "")
        objects = vision_res.get("objects", [])

    elif ext in AUDIO_VIDEO_EXTENSIONS or mime.startswith("audio/") or mime.startswith("video/"):
        logger.info("Processing audio/video evidence: %s", file_path)
        audio_ext = get_audio_extractor()
        audio_res = audio_ext.extract(file_path)
        text_content = audio_res.get("text_content", "")
        metadata["audio_segments"] = audio_res.get("segments", [])

    else:
        logger.info("Processing generic/document evidence: %s", file_path)
        # Attempt to read text directly if file is UTF-8 text
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read(100000)  # Read up to first 100 KB
        except Exception:
            text_content = ""

    return {
        "text_content": text_content,
        "objects": objects,
        "metadata": metadata,
    }