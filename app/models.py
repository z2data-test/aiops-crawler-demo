from datetime import datetime, timezone
from typing import Any, Dict
from pydantic import BaseModel, Field


class PostRecord(BaseModel):
    """
    Validation model for external HTTP endpoint payload item (JSONPlaceholder /posts).
    """
    id: int
    userId: int
    title: str
    body: str


class CrawlerMongoDocument(BaseModel):
    """
    Document schema inserted into MongoDB collection `crawler_results`.
    """
    crawler_id: str
    run_id: str
    source: str
    crawled_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data: Dict[str, Any]
