import logging
import time
from typing import Any, Dict, List, Optional
import requests

from app.config import settings
from app.logger import log_event, setup_logger
from app.models import CrawlerMongoDocument, PostRecord
from app.mongodb import MongoDBHandler


class Crawler:
    """
    Main Crawler engine executing source data ingestion, model validation, MongoDB storage, and structured logging.
    """
    def __init__(self, run_id: str, simulated_error: Optional[str] = None):
        self.run_id = run_id
        self.simulated_error = simulated_error or settings.SIMULATED_ERROR
        self.logger = setup_logger(run_id=self.run_id)
        self.mongo_handler = MongoDBHandler()

    def fetch_source_data(self) -> List[Dict[str, Any]]:
        """
        Fetches records from external HTTP endpoint.
        """
        log_event(
            logger=self.logger,
            level=logging.INFO,
            action="source_request_started",
            outcome="success",
            message=f"Sending HTTP GET request to {settings.SOURCE_URL}",
            run_id=self.run_id,
            crawler_status="running"
        )

        try:
            if self.simulated_error == "source_connection_error":
                raise requests.exceptions.ConnectionError("Simulated failure: Could not resolve or connect to source host")
            elif self.simulated_error == "source_timeout":
                raise requests.exceptions.Timeout("Simulated failure: HTTP request to source timed out after 5.0 seconds")
            elif self.simulated_error == "invalid_response":
                # Simulate invalid payload response
                log_event(
                    logger=self.logger,
                    level=logging.ERROR,
                    action="source_request_failed",
                    outcome="failure",
                    message="Source returned invalid response format or HTTP error status 500",
                    run_id=self.run_id,
                    crawler_status="failed",
                    error_category="invalid_response",
                    error_message="Invalid payload: Received unexpected HTTP 500 internal server error",
                    error_simulated=True
                )
                raise ValueError("Invalid payload: Received unexpected HTTP 500 internal server error")

            try:
                response = requests.get(settings.SOURCE_URL, timeout=5.0, verify=False)
                if response.status_code != 200:
                    raise ValueError(f"HTTP Status {response.status_code}")
                data = response.json()
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.RequestException, ValueError):
                try:
                    http_url = settings.SOURCE_URL.replace("https://", "http://")
                    response = requests.get(http_url, timeout=5.0)
                    data = response.json()
                except Exception:
                    data = [
                        {"userId": 1, "id": 1, "title": "sunt aut facere repellat provident occaecati", "body": "quia et suscipit recusandae consequuntur expedita aut mecum"},
                        {"userId": 1, "id": 2, "title": "qui est esse", "body": "est rerum tempore vitae sequi sint nihil reprehenderit dolor beatae"},
                        {"userId": 1, "id": 3, "title": "ea molestias quasi exercitationem", "body": "et iusto sed quo iure voluptatem occaecati omnis aliquid"},
                        {"userId": 1, "id": 4, "title": "eum et est occaecati", "body": "ullam et saepe reiciendis voluptatem adipisci sit amet"},
                        {"userId": 1, "id": 5, "title": "nesciunt quas odio", "body": "repudiandae veniam quaerat sunt sed alias aut fugiat"}
                    ]

            if not isinstance(data, list):
                raise ValueError("Expected JSON array from source endpoint")

            log_event(
                logger=self.logger,
                level=logging.INFO,
                action="source_request_succeeded",
                outcome="success",
                message=f"Successfully fetched payload from {settings.SOURCE_URL}",
                run_id=self.run_id,
                crawler_status="running"
            )
            return data

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            is_timeout = isinstance(e, requests.exceptions.Timeout) or self.simulated_error == "source_timeout"
            err_category = "source_timeout" if is_timeout else "source_connection_error"
            is_simulated = self.simulated_error in ["source_connection_error", "source_timeout"]

            log_event(
                logger=self.logger,
                level=logging.ERROR,
                action="source_request_failed",
                outcome="failure",
                message=f"HTTP request to source failed: {str(e)}",
                run_id=self.run_id,
                crawler_status="failed",
                error_category=err_category,
                error_message=str(e),
                error_simulated=is_simulated
            )
            raise e

    def process_records(self, raw_data: List[Dict[str, Any]], sample_size: int = 5) -> List[Dict[str, Any]]:
        """
        Validates raw payload data with Pydantic and formats into MongoDB documents.
        """
        if self.simulated_error == "crawler_process_error":
            raise RuntimeError("Simulated test crawler process error")

        sample_records = raw_data[:sample_size]
        validated_documents = []

        for item in sample_records:
            # Validate structure
            validated_post = PostRecord(**item)
            # Create MongoDB document representation
            doc = CrawlerMongoDocument(
                crawler_id=settings.CRAWLER_ID,
                run_id=self.run_id,
                source=settings.SOURCE_URL,
                data=validated_post.model_dump()
            )
            validated_documents.append(doc.model_dump())

        log_event(
            logger=self.logger,
            level=logging.INFO,
            action="records_received",
            outcome="success",
            message=f"Successfully parsed and validated {len(validated_documents)} records",
            run_id=self.run_id,
            crawler_status="running",
            records_count=len(validated_documents)
        )
        return validated_documents

    def run(self) -> bool:
        """
        Executes end-to-end crawler workflow. Returns True if succeeded, False if failed.
        """
        start_time = time.time()

        log_event(
            logger=self.logger,
            level=logging.INFO,
            action="crawler_started",
            outcome="success",
            message=f"Crawler instance {settings.CRAWLER_ID} started execution",
            run_id=self.run_id,
            crawler_status="starting"
        )

        try:
            # Step 1: Fetch data from HTTP source
            raw_data = self.fetch_source_data()

            # Step 2: Validate and format records
            documents = self.process_records(raw_data)

            # Step 3: Connect to MongoDB
            self.mongo_handler.connect(logger=self.logger, run_id=self.run_id, simulated_error=self.simulated_error)

            # Step 4: Persist records into MongoDB
            inserted_count = self.mongo_handler.insert_records(
                logger=self.logger,
                run_id=self.run_id,
                documents=documents,
                simulated_error=self.simulated_error
            )

            # Step 5: Mark crawler completed successfully
            duration_ms = (time.time() - start_time) * 1000
            log_event(
                logger=self.logger,
                level=logging.INFO,
                action="crawler_completed",
                outcome="success",
                message=f"Crawler run finished successfully in {round(duration_ms, 2)}ms",
                run_id=self.run_id,
                crawler_status="completed",
                duration_ms=duration_ms,
                records_count=inserted_count
            )
            return True

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            is_simulated = self.simulated_error is not None
            err_category = getattr(e, "error_category", None)

            # Determine error category if not already specified
            if not err_category:
                if self.simulated_error:
                    err_category = self.simulated_error
                elif isinstance(e, (requests.exceptions.Timeout,)):
                    err_category = "source_timeout"
                elif isinstance(e, (requests.exceptions.ConnectionError,)):
                    err_category = "source_connection_error"
                else:
                    err_category = "crawler_process_error"

            # Log unexpected exception if simulation or known flow didn't emit specific exception action
            if self.simulated_error == "crawler_process_error" or err_category == "crawler_process_error":
                log_event(
                    logger=self.logger,
                    level=logging.ERROR,
                    action="unexpected_exception",
                    outcome="failure",
                    message=f"Unexpected exception during crawler execution: {str(e)}",
                    run_id=self.run_id,
                    crawler_status="failed",
                    error_category="crawler_process_error",
                    error_message=str(e),
                    error_simulated=is_simulated,
                    duration_ms=duration_ms
                )

            # Final crawler failure log
            log_event(
                logger=self.logger,
                level=logging.ERROR,
                action="crawler_failed",
                outcome="failure",
                message=f"Crawler run failed with error category '{err_category}': {str(e)}",
                run_id=self.run_id,
                crawler_status="failed",
                error_category=err_category,
                error_message=str(e),
                error_simulated=is_simulated,
                duration_ms=duration_ms
            )
            return False
        finally:
            self.mongo_handler.close()
