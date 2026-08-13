import logging
import uuid
from unittest.mock import MagicMock, patch
import pytest
from app.crawler import Crawler

SIMULATED_ERRORS = [
    "mongodb_connection_error",
    "mongodb_timeout",
    "database_write_error",
    "source_connection_error",
    "source_timeout",
    "invalid_response",
    "crawler_process_error"
]


class MemoryLogHandler(logging.Handler):
    """
    In-memory logging handler capturing LogRecords for assertion.
    """
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


@pytest.mark.parametrize("error_category", SIMULATED_ERRORS)
@patch("app.crawler.requests.get")
@patch("app.mongodb.MongoClient")
def test_simulated_errors_execution_flow(mock_mongo_client, mock_requests_get, error_category):
    run_id = str(uuid.uuid4())

    # Mock HTTP response for non-network simulated errors
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": 1, "userId": 1, "title": "Test Title", "body": "Test Body"}
    ]
    mock_requests_get.return_value = mock_response

    # Mock Mongo client for non-mongo simulated errors
    mock_client_inst = MagicMock()
    mock_client_inst.admin.command.return_value = {"ok": 1}
    mock_mongo_client.return_value = mock_client_inst

    crawler = Crawler(run_id=run_id, simulated_error=error_category)
    
    memory_handler = MemoryLogHandler()
    crawler.logger.addHandler(memory_handler)

    success = crawler.run()

    # Crawler execution must return False for all error simulation modes
    assert success is False

    # Check that at least one log record contains the expected error category
    error_records = [
        rec for rec in memory_handler.records
        if getattr(rec, "error_category", None) == error_category
    ]
    assert len(error_records) > 0, f"No log record found with error_category '{error_category}'"
    
    for rec in error_records:
        assert getattr(rec, "error_simulated", None) is True
        assert getattr(rec, "run_id", None) == run_id
        assert getattr(rec, "event_outcome", None) == "failure"
