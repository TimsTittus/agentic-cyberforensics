"""
AgentBruce — Unit & Integration Tests for ML Extraction Pipeline
"""

import os
import tempfile
import wave
import pytest
from PIL import Image

from app.workers.extractors import (
    AudioExtractor,
    MetadataExtractor,
    VisionExtractor,
    process_file,
)


@pytest.fixture
def temp_image_file():
    """Create a temporary PNG image file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        img = Image.new("RGB", (200, 100), color=(255, 0, 0))
        img.save(tmp.name)
        file_path = tmp.name

    yield file_path

    if os.path.exists(file_path):
        os.remove(file_path)


@pytest.fixture
def temp_audio_file():
    """Create a temporary 1-second WAV audio file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        file_path = tmp.name

    # Generate a silent 16-bit WAV file
    with wave.open(file_path, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(16000)  # 16 kHz
        silent_frames = b"\x00\x00" * 16000  # 1 second of silence
        wav_file.writeframes(silent_frames)

    yield file_path

    if os.path.exists(file_path):
        os.remove(file_path)


@pytest.fixture
def temp_text_file():
    """Create a temporary text file for testing generic file routing."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as tmp:
        tmp.write("Forensic investigation log sample text content.")
        file_path = tmp.name

    yield file_path

    if os.path.exists(file_path):
        os.remove(file_path)


class TestMetadataExtractor:
    def test_extract_image_metadata(self, temp_image_file):
        extractor = MetadataExtractor()
        meta = extractor.extract(temp_image_file, file_type="image/png")

        assert meta["file_name"] == os.path.basename(temp_image_file)
        assert meta["file_size_bytes"] > 0
        assert meta["extension"] == ".png"
        assert meta["mime_type"] == "image/png"
        assert meta["dimensions"] == {"width": 200, "height": 100}
        assert isinstance(meta["exif"], dict)

    def test_extract_missing_file_raises(self):
        extractor = MetadataExtractor()
        with pytest.raises(FileNotFoundError):
            extractor.extract("/non/existent/path.png")


class TestVisionExtractor:
    def test_vision_extraction_structure(self, temp_image_file):
        extractor = VisionExtractor()
        res = extractor.extract(temp_image_file)

        assert "objects" in res
        assert "text_array" in res
        assert "text_content" in res
        assert isinstance(res["objects"], list)
        assert isinstance(res["text_array"], list)
        assert isinstance(res["text_content"], str)


class TestAudioExtractor:
    def test_audio_extraction_structure(self, temp_audio_file):
        extractor = AudioExtractor()
        res = extractor.extract(temp_audio_file)

        assert "text_content" in res
        assert "segments" in res
        assert isinstance(res["text_content"], str)
        assert isinstance(res["segments"], list)


class TestProcessFileRouting:
    def test_process_image_file(self, temp_image_file):
        artifact = process_file(temp_image_file, file_type="image/png")

        assert "text_content" in artifact
        assert "objects" in artifact
        assert "metadata" in artifact
        assert artifact["metadata"]["mime_type"] == "image/png"

    def test_process_audio_file(self, temp_audio_file):
        artifact = process_file(temp_audio_file, file_type="audio/wav")

        assert "text_content" in artifact
        assert "objects" in artifact
        assert artifact["objects"] == []
        assert "metadata" in artifact
        assert "audio_segments" in artifact["metadata"]

    def test_process_text_file(self, temp_text_file):
        artifact = process_file(temp_text_file, file_type="text/plain")

        assert "Forensic investigation log" in artifact["text_content"]
        assert artifact["objects"] == []
        assert artifact["metadata"]["mime_type"] == "text/plain"