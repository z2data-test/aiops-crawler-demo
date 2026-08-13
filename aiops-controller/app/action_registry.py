from typing import List, Set


class ActionRegistry:
    """
    Security Gatekeeper Check 1: Validates that a recommended action exists in the approved registry.
    """
    APPROVED_ACTIONS: Set[str] = {
        "database_health_check",
        "retry_crawler",
        "notify_devops",
        "restart_crawler"
    }

    @classmethod
    def is_registered(cls, action_name: str) -> bool:
        """
        Returns True if action_name is in the pre-approved action registry, False otherwise.
        """
        if not action_name or not isinstance(action_name, str):
            return False
        return action_name.strip() in cls.APPROVED_ACTIONS

    @classmethod
    def list_approved_actions(cls) -> List[str]:
        return sorted(list(cls.APPROVED_ACTIONS))
