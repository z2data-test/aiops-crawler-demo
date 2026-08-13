import uuid
from unittest.mock import MagicMock
from app.context import ContextCollector
from app.incident import IncidentLifecycleStatus


def test_context_collector_building_incident():
    mock_es = MagicMock()
    run_id = str(uuid.uuid4())

    logs = [
        {"@timestamp": "2026-08-11T12:00:02.000Z", "event": {"action": "mongodb_connection_failed"}},
        {"@timestamp": "2026-08-11T12:00:00.000Z", "event": {"action": "crawler_started"}},
        {"@timestamp": "2026-08-11T12:00:01.000Z", "event": {"action": "source_request_started"}}
    ]
    mock_es.get_logs_by_run_id.return_value = logs

    failure_event = {
        "crawler": {"id": "crawler-001", "name": "simple-crawler", "run_id": run_id, "status": "failed"},
        "event": {"action": "mongodb_connection_failed", "outcome": "failure"},
        "error": {"category": "mongodb_connection_error", "message": "Mongo error", "simulated": True}
    }

    collector = ContextCollector(es_client=mock_es)
    incident = collector.build_incident(failure_event)

    assert incident.incident_id == f"crawler-001:{run_id}"
    assert incident.run_id == run_id
    assert incident.failure_category == "mongodb_connection_error"
    assert incident.status == IncidentLifecycleStatus.DETECTED

    # Assert related logs sorted ascending by @timestamp
    timestamps = [log["@timestamp"] for log in incident.related_logs]
    assert timestamps == [
        "2026-08-11T12:00:00.000Z",
        "2026-08-11T12:00:01.000Z",
        "2026-08-11T12:00:02.000Z"
    ]
