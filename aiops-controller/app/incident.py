from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IncidentLifecycleStatus(str, Enum):
    DETECTED = "DETECTED"
    ANALYZING = "ANALYZING"
    AI_FAILED = "AI_FAILED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    MANUAL_INVESTIGATION = "MANUAL_INVESTIGATION"
    ACTION_PROPOSED = "ACTION_PROPOSED"
    ACTION_VALIDATED = "ACTION_VALIDATED"
    ACTION_REJECTED = "ACTION_REJECTED"
    ACTION_EXECUTING = "ACTION_EXECUTING"
    VERIFYING = "VERIFYING"
    RECOVERED = "RECOVERED"
    UNRESOLVED = "UNRESOLVED"


class Incident(BaseModel):
    """
    Internal model representing a detected crawler failure incident.
    """
    incident_id: str
    crawler_id: str
    crawler_name: str
    run_id: str
    failure_category: str
    failure_message: str
    failure_event: Dict[str, Any]
    related_logs: List[Dict[str, Any]] = Field(default_factory=list)
    detected_at: str
    status: IncidentLifecycleStatus = IncidentLifecycleStatus.DETECTED


class AIAnalysisResult(BaseModel):
    """
    Pydantic schema for structured response from AI Analyzer.
    """
    diagnosis: str
    failure_category: str
    confidence: float
    recommended_action: str
    reason: str
    prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    raw_response: Optional[str] = None

