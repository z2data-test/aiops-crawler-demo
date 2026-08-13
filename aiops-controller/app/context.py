from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.elasticsearch_client import ElasticsearchClient
from app.incident import Incident, IncidentLifecycleStatus


class ContextCollector:
    """
    Collects full context log timeline for a given failure run_id and builds an Incident.
    """
    def __init__(self, es_client: Optional[ElasticsearchClient] = None):
        self.es_client = es_client or ElasticsearchClient()

    def build_incident(self, failure_event: Dict[str, Any]) -> Incident:
        """
        Retrieves all related log records for the run_id, sorts them by timestamp, and creates an Incident.
        """
        crawler = failure_event.get("crawler", {})
        error = failure_event.get("error", {})
        
        crawler_id = crawler.get("id", "crawler-001")
        crawler_name = crawler.get("name", "simple-crawler")
        run_id = crawler.get("run_id", "unknown-run-id")
        
        failure_category = error.get("category") or failure_event.get("error_category") or "unknown_error"
        failure_message = error.get("message") or failure_event.get("message") or "Crawler execution failure"
        
        # Retrieve all log records belonging to this run_id
        related_logs = self.es_client.get_logs_by_run_id(run_id)
        if not related_logs:
            related_logs = [failure_event]
        else:
            # Sort ascending by @timestamp
            related_logs = sorted(related_logs, key=lambda x: x.get("@timestamp", ""))

        incident_id = f"{crawler_id}:{run_id}"
        detected_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        return Incident(
            incident_id=incident_id,
            crawler_id=crawler_id,
            crawler_name=crawler_name,
            run_id=run_id,
            failure_category=failure_category,
            failure_message=failure_message,
            failure_event=failure_event,
            related_logs=related_logs,
            detected_at=detected_at,
            status=IncidentLifecycleStatus.DETECTED
        )
