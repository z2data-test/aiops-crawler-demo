from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import requests
from app.config import settings


class ElasticsearchClient:
    """
    Client for querying crawler logs and writing controller audit events to Elasticsearch.
    """
    def __init__(
        self,
        es_url: str = settings.ELASTICSEARCH_URL,
        crawler_index: str = settings.ELASTICSEARCH_CRAWLER_INDEX,
        controller_index: str = settings.ELASTICSEARCH_CONTROLLER_INDEX
    ):
        self.es_url = es_url.rstrip("/")
        self.crawler_index = crawler_index
        self.controller_index = controller_index

    def search_failures(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Searches crawler index for failure events (event.outcome = "failure").
        """
        url = f"{self.es_url}/{self.crawler_index}/_search"
        query = {
            "size": limit,
            "sort": [{"@timestamp": {"order": "desc"}}],
            "query": {
                "bool": {
                    "must": [
                        {"term": {"event.outcome.keyword": "failure"}}
                    ]
                }
            }
        }
        try:
            res = requests.post(url, json=query, timeout=5.0)
            if res.status_code == 200:
                hits = res.json().get("hits", {}).get("hits", [])
                return [hit.get("_source", {}) for hit in hits]
            return []
        except Exception:
            return []

    def get_logs_by_run_id(self, run_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieves all log records sharing the specified run_id, sorted by timestamp ascending.
        """
        url = f"{self.es_url}/{self.crawler_index}/_search"
        query = {
            "size": limit,
            "sort": [{"@timestamp": {"order": "asc"}}],
            "query": {
                "term": {
                    "crawler.run_id.keyword": run_id
                }
            }
        }
        try:
            res = requests.post(url, json=query, timeout=5.0)
            if res.status_code == 200:
                hits = res.json().get("hits", {}).get("hits", [])
                return [hit.get("_source", {}) for hit in hits]
            return []
        except Exception:
            return []

    def incident_exists(self, incident_id: str) -> bool:
        """
        Checks whether an incident has already been processed and stored in the controller index.
        """
        url = f"{self.es_url}/{self.controller_index}-*/_search"
        query = {
            "size": 1,
            "query": {
                "term": {
                    "incident.id.keyword": incident_id
                }
            }
        }
        try:
            res = requests.post(url, json=query, timeout=5.0)
            if res.status_code == 200:
                total = res.json().get("hits", {}).get("total", {})
                value = total.get("value", 0) if isinstance(total, dict) else total
                return value > 0
            return False
        except Exception:
            return False

    def write_controller_event(self, event_document: Dict[str, Any]) -> bool:
        """
        Writes a controller lifecycle audit record into Elasticsearch under daily index pattern.
        """
        date_str = datetime.now(timezone.utc).strftime("%Y.%m.%d")
        target_index = f"{self.controller_index}-{date_str}"
        url = f"{self.es_url}/{target_index}/_doc"
        
        headers = {"Content-Type": "application/json"}
        try:
            res = requests.post(url, json=event_document, headers=headers, timeout=5.0)
            return res.status_code in [200, 201]
        except Exception:
            return False
