import argparse
import sys
import time
from typing import Any, Optional

from app.action_executor import ActionExecutor
from app.action_policy import ActionPolicy
from app.action_registry import ActionRegistry
from app.ai_analyzer import NvidiaAIAnalyzer
from app.config import settings
from app.context import ContextCollector
from app.detector import FailureDetector
from app.elasticsearch_client import ElasticsearchClient
from app.incident import Incident, IncidentLifecycleStatus
from app.logger import setup_logger
from app.verifier import IncidentVerifier

logger = setup_logger()


class AIOpsController:
    """
    Main AIOps Controller service orchestrating incident lifecycle transitions.
    """
    def __init__(self):
        self.es_client = ElasticsearchClient()
        self.detector = FailureDetector(es_client=self.es_client)
        self.collector = ContextCollector(es_client=self.es_client)
        self.ai_analyzer = NvidiaAIAnalyzer()
        self.executor = ActionExecutor()
        self.verifier = IncidentVerifier()

    def process_incident(self, failure_event: dict) -> IncidentLifecycleStatus:
        """
        Executes end-to-end incident lifecycle state transitions.
        """
        # Step 1: Detect failure and construct Incident context
        incident = self.collector.build_incident(failure_event)
        incident.status = IncidentLifecycleStatus.DETECTED

        self._emit_audit(
            incident=incident,
            event_action="incident_detected",
            event_outcome="success",
            message=f"Incident {incident.incident_id} detected for crawler {incident.crawler_id}"
        )

        # Step 2: AI Analysis
        incident.status = IncidentLifecycleStatus.ANALYZING
        self._emit_audit(
            incident=incident,
            event_action="ai_analysis_started",
            event_outcome="success",
            message=f"Sending incident {incident.incident_id} context to NVIDIA AI for analysis"
        )

        ai_result = self.ai_analyzer.analyze_incident(incident)
        if not ai_result:
            incident.status = IncidentLifecycleStatus.AI_FAILED
            self._emit_audit(
                incident=incident,
                event_action="ai_analysis_failed",
                event_outcome="failure",
                message="NVIDIA AI analysis failed or returned malformed data"
            )
            return IncidentLifecycleStatus.AI_FAILED

        # Confidence Threshold Check
        if ai_result.confidence < settings.AI_CONFIDENCE_THRESHOLD:
            incident.status = IncidentLifecycleStatus.MANUAL_INVESTIGATION
            self._emit_audit(
                incident=incident,
                event_action="ai_confidence_low",
                event_outcome="failure",
                message=f"AI confidence ({ai_result.confidence}) below threshold ({settings.AI_CONFIDENCE_THRESHOLD}). Marked for manual investigation.",
                ai_result=ai_result
            )
            return IncidentLifecycleStatus.MANUAL_INVESTIGATION

        incident.status = IncidentLifecycleStatus.ACTION_PROPOSED
        self._emit_audit(
            incident=incident,
            event_action="action_proposed",
            event_outcome="success",
            message=f"AI recommended action '{ai_result.recommended_action}' with confidence {ai_result.confidence}",
            ai_result=ai_result
        )

        # Step 3: Security Gatekeeper Validation (Check 1 & Check 2)
        rec_action = ai_result.recommended_action

        # Check 1: Action Registry
        if not ActionRegistry.is_registered(rec_action):
            incident.status = IncidentLifecycleStatus.ACTION_REJECTED
            self._emit_audit(
                incident=incident,
                event_action="action_rejected",
                event_outcome="failure",
                message=f"Security Gatekeeper Check 1 Failed: Action '{rec_action}' is not in approved Action Registry.",
                ai_result=ai_result,
                action_name=rec_action,
                action_status="rejected_unregistered"
            )
            return IncidentLifecycleStatus.ACTION_REJECTED

        # Check 2: Action Policy
        if not ActionPolicy.is_allowed(incident.failure_category, rec_action):
            incident.status = IncidentLifecycleStatus.ACTION_REJECTED
            self._emit_audit(
                incident=incident,
                event_action="action_rejected",
                event_outcome="failure",
                message=f"Security Gatekeeper Check 2 Failed: Action '{rec_action}' is not authorized for failure category '{incident.failure_category}'.",
                ai_result=ai_result,
                action_name=rec_action,
                action_status="rejected_policy_mismatch"
            )
            return IncidentLifecycleStatus.ACTION_REJECTED

        incident.status = IncidentLifecycleStatus.ACTION_VALIDATED
        self._emit_audit(
            incident=incident,
            event_action="action_validated",
            event_outcome="success",
            message=f"Action '{rec_action}' passed Security Gatekeeper (Registry & Policy checks).",
            ai_result=ai_result,
            action_name=rec_action,
            action_status="validated"
        )

        # Step 4: Execute Action
        incident.status = IncidentLifecycleStatus.ACTION_EXECUTING
        self._emit_audit(
            incident=incident,
            event_action="action_executing",
            event_outcome="success",
            message=f"Executing action handler '{rec_action}'",
            ai_result=ai_result,
            action_name=rec_action,
            action_status="executing"
        )

        action_result = self.executor.execute(rec_action)

        # Step 5: Verification
        incident.status = IncidentLifecycleStatus.VERIFYING
        final_status = self.verifier.verify(action_result)
        incident.status = final_status

        outcome_str = "success" if final_status == IncidentLifecycleStatus.RECOVERED else "failure"
        self._emit_audit(
            incident=incident,
            event_action="incident_lifecycle_completed",
            event_outcome=outcome_str,
            message=f"Incident lifecycle completed with final status '{final_status.value}'. Details: {action_result.get('details')}",
            ai_result=ai_result,
            action_name=rec_action,
            action_status="executed",
            verification_status=final_status.value
        )

        return final_status

    def _emit_audit(
        self,
        incident: Incident,
        event_action: str,
        event_outcome: str,
        message: str,
        ai_result: Optional[Any] = None,
        action_name: Optional[str] = None,
        action_status: Optional[str] = None,
        verification_status: Optional[str] = None
    ):
        extra = {
            "incident_id": incident.incident_id,
            "crawler_id": incident.crawler_id,
            "crawler_run_id": incident.run_id,
            "event_action": event_action,
            "event_outcome": event_outcome
        }
        if ai_result:
            extra["ai_diagnosis"] = ai_result.diagnosis
            extra["ai_confidence"] = ai_result.confidence
            extra["ai_recommended_action"] = ai_result.recommended_action
        if action_name:
            extra["action_name"] = action_name
        if action_status:
            extra["action_status"] = action_status
        if verification_status:
            extra["verification_status"] = verification_status

        log_level = 20 if event_outcome == "success" else 40
        logger.log(log_level, message, extra=extra)

        # Also write audit document to Elasticsearch controller index
        audit_doc = {
            "@timestamp": incident.detected_at,
            "service": {"name": "aiops-controller"},
            "incident": {"id": incident.incident_id, "status": incident.status.value},
            "crawler": {"id": incident.crawler_id, "name": incident.crawler_name, "run_id": incident.run_id},
            "event": {"action": event_action, "outcome": event_outcome},
            "message": message
        }
        if ai_result:
            audit_doc["ai"] = {
                "diagnosis": ai_result.diagnosis,
                "confidence": ai_result.confidence,
                "recommended_action": ai_result.recommended_action,
                "reason": ai_result.reason
            }
            if ai_result.prompt:
                audit_doc["ai"]["prompt"] = ai_result.prompt
            if ai_result.system_prompt:
                audit_doc["ai"]["system_prompt"] = ai_result.system_prompt
            if ai_result.raw_response:
                audit_doc["ai"]["raw_response"] = ai_result.raw_response
        if action_name or action_status:
            audit_doc["action"] = {"name": action_name or "none", "status": action_status or "none"}
        if verification_status:
            audit_doc["verification"] = {"status": verification_status}

        self.es_client.write_controller_event(audit_doc)

    def run_once(self) -> int:
        failures = self.detector.detect_unprocessed_failures()
        processed_count = 0
        for failure_event in failures:
            self.process_incident(failure_event)
            processed_count += 1
        return processed_count

    def run_loop(self):
        logger.info(f"Starting AIOps Controller service loop (Poll interval: {settings.POLL_INTERVAL_SECONDS}s)")
        while True:
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error in controller loop: {str(e)}")
            time.sleep(settings.POLL_INTERVAL_SECONDS)


def main():
    parser = argparse.ArgumentParser(description="AIOps Controller Service")
    parser.add_argument("--once", action="store_true", help="Run a single pass of failure detection and exit.")
    args = parser.parse_args()

    controller = AIOpsController()
    if args.once:
        count = controller.run_once()
        logger.info(f"Single pass complete. Processed {count} failure incident(s).")
        sys.exit(0)
    else:
        controller.run_loop()


if __name__ == "__main__":
    main()
