"""
AgentBruce — Unit & Integration Tests for Celery Worker Tasks
"""

import uuid
from unittest.mock import MagicMock, patch
import pytest

from app.workers.tasks import route_evidence


class TestRouteEvidenceTask:
    @patch("app.workers.tasks.psycopg2.connect")
    @patch("app.workers.tasks.process_file")
    def test_route_evidence_success(self, mock_process_file, mock_db_connect):
        # 1. Setup mock database cursor and connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock DB row returned after status set to 'processing'
        evidence_id = str(uuid.uuid4())
        mock_cursor.fetchone.return_value = {
            "id": evidence_id,
            "file_path": "/tmp/test_evidence.png",
            "file_type": "image/png",
            "processed_status": "processing",
        }

        # Mock ML extraction output
        expected_artifact = {
            "text_content": "Extracted OCR text",
            "objects": [{"label": "laptop", "confidence": 0.98, "box": [10, 10, 100, 100]}],
            "metadata": {"file_name": "test_evidence.png"},
        }
        mock_process_file.return_value = expected_artifact

        # 2. Execute Celery task directly
        result = route_evidence(evidence_id)

        # 3. Assertions
        assert result["evidence_id"] == evidence_id
        assert result["status"] == "completed"
        assert result["artifact"] == expected_artifact
        mock_process_file.assert_called_once_with(
            file_path="/tmp/test_evidence.png",
            file_type="image/png",
        )
        assert mock_cursor.execute.call_count >= 2  # 1st for update to processing, 2nd for update to completed

    @patch("app.workers.tasks.psycopg2.connect")
    def test_route_evidence_not_found(self, mock_db_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_db_connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None  # No matching pending evidence record

        evidence_id = str(uuid.uuid4())
        result = route_evidence(evidence_id)

        assert result["status"] == "skipped"
        assert result["evidence_id"] == evidence_id