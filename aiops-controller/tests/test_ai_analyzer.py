import json
import uuid
from unittest.mock import MagicMock, patch
from app.ai_analyzer import NvidiaAIAnalyzer
from app.incident import Incident, IncidentLifecycleStatus


def test_nvidia_ai_analyzer_demo_fallback():
    run_id = str(uuid.uuid4())
    incident = Incident(
        incident_id=f"crawler-001:{run_id}",
        crawler_id="crawler-001",
        crawler_name="simple-crawler",
        run_id=run_id,
        failure_category="mongodb_connection_error",
        failure_message="Connection timed out",
        failure_event={"event": {"action": "mongodb_connection_failed"}},
        related_logs=[],
        detected_at="2026-08-11T12:00:00.000Z",
        status=IncidentLifecycleStatus.ANALYZING
    )

    analyzer = NvidiaAIAnalyzer(api_key="demo_key")
    result = analyzer.analyze_incident(incident)

    assert result is not None
    assert result.recommended_action == "database_health_check"
    assert result.confidence == 0.95
    assert result.failure_category == "mongodb_connection_error"


@patch("app.ai_analyzer.requests.post")
def test_nvidia_ai_analyzer_real_mock_response(mock_post):
    run_id = str(uuid.uuid4())
    incident = Incident(
        incident_id=f"crawler-001:{run_id}",
        crawler_id="crawler-001",
        crawler_name="simple-crawler",
        run_id=run_id,
        failure_category="mongodb_timeout",
        failure_message="Mongo timeout",
        failure_event={},
        related_logs=[],
        detected_at="2026-08-11T12:00:00.000Z"
    )

    ai_json = {
        "diagnosis": "MongoDB server selection timeout",
        "failure_category": "mongodb_timeout",
        "confidence": 0.92,
        "recommended_action": "database_health_check",
        "reason": "Connection attempt to database timed out."
    }

    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "choices": [{"message": {"content": json.dumps(ai_json)}}]
    }
    mock_post.return_value = mock_res

    with patch("app.ai_analyzer.settings.AIOPS_DEMO_MODE", False):
        analyzer = NvidiaAIAnalyzer(api_key="real_key_for_test")
        result = analyzer.analyze_incident(incident)

        assert result is not None
        assert result.recommended_action == "database_health_check"
        assert result.confidence == 0.92
