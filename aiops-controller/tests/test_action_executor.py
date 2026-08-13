from unittest.mock import MagicMock, patch
from app.action_executor import ActionExecutor


@patch("actions.database_health_check.MongoClient")
def test_action_executor_database_health_check_success(mock_mongo):
    mock_client_inst = MagicMock()
    mock_client_inst.admin.command.return_value = {"ok": 1}
    mock_mongo.return_value = mock_client_inst

    executor = ActionExecutor(mongodb_uri="mongodb://localhost:27017")
    res = executor.execute("database_health_check")

    assert res["action"] == "database_health_check"
    assert res["success"] is True
    assert "reachable" in res["details"]


def test_action_executor_demo_actions():
    executor = ActionExecutor(demo_mode=True)

    res_retry = executor.execute("retry_crawler")
    assert res_retry["action"] == "retry_crawler"
    assert res_retry["success"] is True

    res_notify = executor.execute("notify_devops")
    assert res_notify["action"] == "notify_devops"
    assert res_notify["success"] is True

    res_restart = executor.execute("restart_crawler")
    assert res_restart["action"] == "restart_crawler"
    assert res_restart["success"] is True
    assert "disabled in demo mode" in res_restart["details"]


def test_action_executor_arbitrary_command_rejection():
    executor = ActionExecutor()
    res = executor.execute("powershell Restart-Service MongoDB")

    assert res["success"] is False
    assert "Unrecognized or unapproved" in res["details"]
