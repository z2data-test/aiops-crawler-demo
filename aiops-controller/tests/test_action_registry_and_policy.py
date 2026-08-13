from app.action_policy import ActionPolicy
from app.action_registry import ActionRegistry


def test_action_registry_check_1():
    # Check approved actions
    assert ActionRegistry.is_registered("database_health_check") is True
    assert ActionRegistry.is_registered("retry_crawler") is True
    assert ActionRegistry.is_registered("notify_devops") is True
    assert ActionRegistry.is_registered("restart_crawler") is True

    # Security check: Reject unapproved or arbitrary shell strings
    assert ActionRegistry.is_registered("delete_database") is False
    assert ActionRegistry.is_registered("powershell Restart-Service MongoDB") is False
    assert ActionRegistry.is_registered("rm -rf /") is False
    assert ActionRegistry.is_registered("") is False


def test_action_policy_check_2():
    # Check authorized failure-to-action policy pairs
    assert ActionPolicy.is_allowed("mongodb_connection_error", "database_health_check") is True
    assert ActionPolicy.is_allowed("mongodb_timeout", "database_health_check") is True
    assert ActionPolicy.is_allowed("database_write_error", "retry_crawler") is True
    assert ActionPolicy.is_allowed("source_connection_error", "retry_crawler") is True
    assert ActionPolicy.is_allowed("source_timeout", "retry_crawler") is True
    assert ActionPolicy.is_allowed("invalid_response", "notify_devops") is True
    assert ActionPolicy.is_allowed("crawler_process_error", "restart_crawler") is True

    # Policy Violation Check: Reject registered actions that mismatch failure category
    # Example: restart_crawler for mongodb_connection_error must be REJECTED!
    assert ActionPolicy.is_allowed("mongodb_connection_error", "restart_crawler") is False
    assert ActionPolicy.is_allowed("mongodb_connection_error", "retry_crawler") is False
    assert ActionPolicy.is_allowed("invalid_response", "database_health_check") is False
