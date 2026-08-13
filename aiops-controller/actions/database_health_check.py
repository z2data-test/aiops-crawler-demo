from typing import Any, Dict
from pymongo import MongoClient
from pymongo.errors import PyMongoError


def run(mongodb_uri: str) -> Dict[str, Any]:
    """
    Performs a read-only MongoDB ping check to verify database availability.
    Does NOT modify database content.
    """
    try:
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        client.close()
        return {
            "action": "database_health_check",
            "success": True,
            "details": "MongoDB is reachable and healthy"
        }
    except PyMongoError as e:
        return {
            "action": "database_health_check",
            "success": False,
            "details": f"MongoDB is unavailable: {str(e)}"
        }
    except Exception as e:
        return {
            "action": "database_health_check",
            "success": False,
            "details": f"Database health check failed: {str(e)}"
        }
