import uuid
from unittest.mock import MagicMock, patch
import pytest
from app.crawler import Crawler


@patch("app.crawler.requests.get")
@patch("app.crawler.MongoDBHandler")
def test_successful_crawler_run(mock_mongo_cls, mock_requests_get):
    run_id = str(uuid.uuid4())

    # Mock HTTP response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"id": 1, "userId": 1, "title": "Test Title 1", "body": "Test Body 1"},
        {"id": 2, "userId": 1, "title": "Test Title 2", "body": "Test Body 2"}
    ]
    mock_requests_get.return_value = mock_response

    # Mock Mongo Handler
    mock_mongo_inst = MagicMock()
    mock_mongo_inst.insert_records.return_value = 2
    mock_mongo_cls.return_value = mock_mongo_inst

    crawler = Crawler(run_id=run_id)
    success = crawler.run()

    assert success is True
    mock_requests_get.assert_called_once()
    mock_mongo_inst.connect.assert_called_once()
    mock_mongo_inst.insert_records.assert_called_once()
    mock_mongo_inst.close.assert_called_once()
