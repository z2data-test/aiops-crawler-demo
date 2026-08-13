import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from app.config import settings


class ControllerJSONFormatter(logging.Formatter):
    """
    JSON Formatter enforcing structured log output aligned with ECS specs for AIOps Controller.
    """
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        log_data: Dict[str, Any] = {
            "@timestamp": timestamp,
            "service": {
                "name": "aiops-controller"
            },
            "log": {
                "level": record.levelname
            },
            "message": record.getMessage()
        }

        # Event fields
        action = getattr(record, "event_action", None)
        outcome = getattr(record, "event_outcome", None)
        if action or outcome:
            log_data["event"] = {
                "action": action or "controller_event",
                "outcome": outcome or "success"
            }

        # Incident fields
        incident_id = getattr(record, "incident_id", None)
        if incident_id:
            log_data["incident"] = {"id": incident_id}

        # Crawler context fields
        crawler_id = getattr(record, "crawler_id", None)
        crawler_run_id = getattr(record, "crawler_run_id", None)
        if crawler_id or crawler_run_id:
            log_data["crawler"] = {
                "id": crawler_id or "unknown",
                "run_id": crawler_run_id or "unknown"
            }

        # AI analysis fields
        ai_diagnosis = getattr(record, "ai_diagnosis", None)
        ai_confidence = getattr(record, "ai_confidence", None)
        ai_rec_action = getattr(record, "ai_recommended_action", None)
        ai_prompt = getattr(record, "ai_prompt", None)
        ai_system_prompt = getattr(record, "ai_system_prompt", None)
        ai_raw_response = getattr(record, "ai_raw_response", None)
        if ai_diagnosis or ai_confidence is not None or ai_rec_action or ai_prompt or ai_system_prompt or ai_raw_response:
            ai_dict: Dict[str, Any] = {}
            if ai_diagnosis:
                ai_dict["diagnosis"] = ai_diagnosis
            if ai_confidence is not None:
                ai_dict["confidence"] = ai_confidence
            if ai_rec_action:
                ai_dict["recommended_action"] = ai_rec_action
            if ai_prompt:
                ai_dict["prompt"] = ai_prompt
            if ai_system_prompt:
                ai_dict["system_prompt"] = ai_system_prompt
            if ai_raw_response:
                ai_dict["raw_response"] = ai_raw_response
            log_data["ai"] = ai_dict

        # Action fields
        action_name = getattr(record, "action_name", None)
        action_status = getattr(record, "action_status", None)
        if action_name or action_status:
            log_data["action"] = {
                "name": action_name or "none",
                "status": action_status or "none"
            }

        # Verification fields
        verification_status = getattr(record, "verification_status", None)
        if verification_status:
            log_data["verification"] = {"status": verification_status}

        return json.dumps(log_data)


def setup_logger(log_level: str = settings.LOG_LEVEL) -> logging.Logger:
    logger = logging.getLogger("aiops_controller")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    formatter = ControllerJSONFormatter()

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    logger.addHandler(stdout_handler)

    return logger
