from typing import Any, Dict
from actions import database_health_check, notify_devops, restart_crawler, retry_crawler
from app.config import settings


class ActionExecutor:
    """
    Executes approved remediation actions through explicit Python functions.
    Does NOT accept or execute arbitrary shell/PowerShell commands.
    """
    def __init__(self, mongodb_uri: str = settings.MONGODB_URI, demo_mode: bool = settings.AIOPS_DEMO_MODE):
        self.mongodb_uri = mongodb_uri
        self.demo_mode = demo_mode

    def execute(self, action_name: str) -> Dict[str, Any]:
        """
        Routes validated action_name string to explicit Python module handler.
        """
        clean_action = action_name.strip() if action_name else ""

        if clean_action == "database_health_check":
            return database_health_check.run(self.mongodb_uri)
        elif clean_action == "retry_crawler":
            return retry_crawler.run(self.demo_mode)
        elif clean_action == "notify_devops":
            return notify_devops.run(self.demo_mode)
        elif clean_action == "restart_crawler":
            return restart_crawler.run(self.demo_mode)
        else:
            return {
                "action": clean_action,
                "success": False,
                "details": f"Unrecognized or unapproved action execution attempt: '{clean_action}'"
            }
