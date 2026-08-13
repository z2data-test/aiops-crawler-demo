import json
import logging
import uuid
import pytest
from app.logger import StructuredJSONFormatter, log_event


def test_structured_json_formatter_valid_output():
    run_id = str(uuid.uuid4())
    formatter = StructuredJSONFormatter(run_id=run_id, crawler_status="running")

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_path.py",
        lineno=10,
        msg="Test log message",
        args=(),
        exc_info=None
    )
    record.run_id = run_id
    record.event_action = "crawler_started"
    record.event_outcome = "success"

    json_str = formatter.format(record)
    data = json.loads(json_str)

    assert "@timestamp" in data
    assert data["service"]["name"] == "simple-crawler"
    assert data["environment"] == "demo"
    assert data["crawler"]["id"] == "crawler-001"
    assert data["crawler"]["name"] == "simple-crawler"
    assert data["crawler"]["run_id"] == run_id
    assert data["crawler"]["status"] == "running"
    assert data["event"]["action"] == "crawler_started"
    assert data["event"]["outcome"] == "success"
    assert data["log"]["level"] == "INFO"
    assert data["message"] == "Test log message"


def test_structured_json_formatter_error_simulated():
    run_id = str(uuid.uuid4())
    formatter = StructuredJSONFormatter(run_id=run_id, crawler_status="failed")

    record = logging.LogRecord(
        name="test_logger",
        level=logging.ERROR,
        pathname="test_path.py",
        lineno=20,
        msg="Failed to connect to Mongo",
        args=(),
        exc_info=None
    )
    record.run_id = run_id
    record.event_action = "mongodb_connection_failed"
    record.event_outcome = "failure"
    record.error_category = "mongodb_connection_error"
    record.error_message = "Connection refused"
    record.error_simulated = True

    json_str = formatter.format(record)
    data = json.loads(json_str)

    assert data["error"]["category"] == "mongodb_connection_error"
    assert data["error"]["message"] == "Connection refused"
    assert data["error"]["simulated"] is True
