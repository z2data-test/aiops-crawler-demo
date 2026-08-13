from app.incident import IncidentLifecycleStatus
from app.verifier import IncidentVerifier


def test_verifier_success():
    verifier = IncidentVerifier()
    status = verifier.verify({"action": "database_health_check", "success": True, "details": "Healthy"})
    assert status == IncidentLifecycleStatus.RECOVERED


def test_verifier_failure():
    verifier = IncidentVerifier()
    status = verifier.verify({"action": "database_health_check", "success": False, "details": "Unavailable"})
    assert status == IncidentLifecycleStatus.UNRESOLVED
