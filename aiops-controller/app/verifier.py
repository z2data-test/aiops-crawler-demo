from typing import Any, Dict
from app.incident import IncidentLifecycleStatus


class IncidentVerifier:
    """
    Verifies action execution outcome and determines final incident status.
    """
    def verify(self, action_result: Dict[str, Any]) -> IncidentLifecycleStatus:
        """
        Evaluates execution outcome. Returns RECOVERED if successful, UNRESOLVED if failed.
        """
        success = action_result.get("success", False)
        if success:
            return IncidentLifecycleStatus.RECOVERED
        return IncidentLifecycleStatus.UNRESOLVED
