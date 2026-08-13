import uuid
from unittest.mock import MagicMock
from app.detector import FailureDetector


def test_failure_detector_deduplication():
    mock_es = MagicMock()
    run_id = str(uuid.uuid4())
    failure_event = {
        "@timestamp": "2026-08-11T12:00:00.000Z",
        "crawler": {"id": "crawler-001", "name": "simple-crawler", "run_id": run_id, "status": "failed"},
        "event": {"action": "mongodb_connection_failed", "outcome": "failure"},
        "error": {"category": "mongodb_connection_error", "message": "Connection failed", "simulated": True}
    }

    mock_es.search_failures.return_value = [failure_event]
    mock_es.incident_exists.return_value = False

    detector = FailureDetector(es_client=mock_es)

    # First call: detects new failure
    detected = detector.detect_unprocessed_failures()
    assert len(detected) == 1
    assert detected[0]["crawler"]["run_id"] == run_id

    # Second call: deduplicated via in-memory cache
    detected_again = detector.detect_unprocessed_failures()
    assert len(detected_again) == 0


def test_failure_detector_es_persistence_deduplication():
    mock_es = MagicMock()
    run_id = str(uuid.uuid4())
    failure_event = {
        "crawler": {"id": "crawler-001", "name": "simple-crawler", "run_id": run_id},
        "event": {"outcome": "failure"}
    }

    mock_es.search_failures.return_value = [failure_event]
    mock_es.incident_exists.return_value = True  # ES indicates incident already exists

    detector = FailureDetector(es_client=mock_es)
    detected = detector.detect_unprocessed_failures()

    assert len(detected) == 0
