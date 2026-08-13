from typing import Dict, List


class ActionPolicy:
    """
    Security Gatekeeper Check 2: Validates that a recommended action is allowed for the specific failure category.
    """
    POLICY_MAP: Dict[str, List[str]] = {
        "mongodb_connection_error": ["database_health_check"],
        "mongodb_timeout": ["database_health_check"],
        "database_write_error": ["retry_crawler"],
        "source_connection_error": ["retry_crawler"],
        "source_timeout": ["retry_crawler"],
        "invalid_response": ["notify_devops"],
        "crawler_process_error": ["restart_crawler"]
    }

    @classmethod
    def is_allowed(cls, failure_category: str, action_name: str) -> bool:
        """
        Returns True if action_name is authorized for the specified failure_category by policy.
        """
        if not failure_category or not action_name:
            return False
        allowed_actions = cls.POLICY_MAP.get(failure_category, [])
        return action_name.strip() in allowed_actions

    @classmethod
    def get_allowed_actions(cls, failure_category: str) -> List[str]:
        return cls.POLICY_MAP.get(failure_category, [])
