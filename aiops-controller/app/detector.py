from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from app.elasticsearch_client import ElasticsearchClient


class FailureDetector:
    """
    Scans Elasticsearch for crawler failure events and deduplicates processed incidents.
    """
    def __init__(self, es_client: Optional[ElasticsearchClient] = None):
        self.es_client = es_client or ElasticsearchClient()
        self.seen_incidents: Set[str] = set()

    def detect_unprocessed_failures(self) -> List[Dict[str, Any]]:
        """
        Retrieves crawler failure events that have not yet been processed.
        """
        raw_failures = self.es_client.search_failures()
        unprocessed = []

        for event in raw_failures:
            crawler = event.get("crawler", {})
            crawler_id = crawler.get("id", "crawler-001")
            run_id = crawler.get("run_id")

            if not run_id:
                continue

            incident_id = f"{crawler_id}:{run_id}"

            # Deduplication Check 1: In-memory set
            if incident_id in self.seen_incidents:
                continue

            # Deduplication Check 2: Elasticsearch controller index persistence
            if self.es_client.incident_exists(incident_id):
                self.seen_incidents.add(incident_id)
                continue

            # Add to local cache and include in return list
            self.seen_incidents.add(incident_id)
            unprocessed.append(event)

        return unprocessed
