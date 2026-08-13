from typing import Any, Dict


def run(demo_mode: bool = True) -> Dict[str, Any]:
    """
    Handles restart_crawler action.
    """
    return {
        "action": "restart_crawler",
        "success": True,
        "details": "Restart requested but disabled in demo mode"
    }
