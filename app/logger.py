import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.config import settings


class StructuredJSONFormatter(logging.Formatter):
    """
    JSON Formatter enforcing structured log output aligned with Elastic Common Schema (ECS) light specs.
    """
    def __init__(self, run_id: Optional[str] = None, crawler_status: str = "running"):
        super().__init__()
        self.default_run_id = run_id
        self.default_crawler_status = crawler_status

    def format(self, record: logging.LogRecord) -> str:
        # Standardized UTC ISO8601 timestamp with millisecond precision
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        run_id = getattr(record, "run_id", self.default_run_id or "unknown-run-id")
        crawler_status = getattr(record, "crawler_status", self.default_crawler_status)
        event_action = getattr(record, "event_action", "unknown_action")
        event_outcome = getattr(record, "event_outcome", "success")

        log_data: Dict[str, Any] = {
            "@timestamp": timestamp,
            "service": {
                "name": settings.CRAWLER_NAME
            },
            "environment": settings.ENVIRONMENT,
            "crawler": {
                "id": settings.CRAWLER_ID,
                "name": settings.CRAWLER_NAME,
                "run_id": run_id,
                "status": crawler_status
            },
            "event": {
                "action": event_action,
                "outcome": event_outcome
            },
            "log": {
                "level": record.levelname
            },
            "message": record.getMessage()
        }

        # Handle Error attributes if present
        error_category = getattr(record, "error_category", None)
        error_message = getattr(record, "error_message", None)
        error_simulated = getattr(record, "error_simulated", None)

        if error_category is not None or error_message is not None or error_simulated is not None:
            err_dict: Dict[str, Any] = {}
            if error_category is not None:
                err_dict["category"] = error_category
            err_dict["simulated"] = bool(error_simulated) if error_simulated is not None else False
            if error_message is not None:
                err_dict["message"] = str(error_message)
            log_data["error"] = err_dict

        # Metric fields
        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            log_data["duration_ms"] = round(float(duration_ms), 2)

        records_count = getattr(record, "records_count", None)
        if records_count is not None:
            log_data["records"] = {"count": int(records_count)}

        return json.dumps(log_data)


def setup_logger(run_id: str, log_level: str = settings.LOG_LEVEL, log_file_path: str = settings.LOG_FILE_PATH) -> logging.Logger:
    """
    Initializes and configures application logger with stdout StreamHandler and FileHandler.
    """
    logger = logging.getLogger("simple_crawler")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    formatter = StructuredJSONFormatter(run_id=run_id, crawler_status="running")

    # 1. Stdout Handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    # 2. File Handler (Ensure directory exists)
    if log_file_path:
        log_dir = os.path.dirname(log_file_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_event(
    logger: logging.Logger,
    level: int,
    action: str,
    outcome: str,
    message: str,
    run_id: str,
    crawler_status: str = "running",
    error_category: Optional[str] = None,
    error_message: Optional[str] = None,
    error_simulated: Optional[bool] = None,
    duration_ms: Optional[float] = None,
    records_count: Optional[int] = None
) -> None:
    """
    Helper function to emit structured logs with consistent extra dictionary attributes.
    """
    extra: Dict[str, Any] = {
        "run_id": run_id,
        "crawler_status": crawler_status,
        "event_action": action,
        "event_outcome": outcome,
    }
    if error_category is not None:
        extra["error_category"] = error_category
    if error_message is not None:
        extra["error_message"] = error_message
    if error_simulated is not None:
        extra["error_simulated"] = error_simulated
    if duration_ms is not None:
        extra["duration_ms"] = duration_ms
    if records_count is not None:
        extra["records_count"] = records_count

    logger.log(level, message, extra=extra)
