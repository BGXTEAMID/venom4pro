from bgxdesk.services.analysis import AuditAnalytics, FindingAnalytics, ScanAnalytics, redact_text
from bgxdesk.services.inventory import InventoryService, ToolSpec


def test_finding_analytics_risk_and_queue() -> None:
    findings = [
        {"id": "1", "title": "Missing auth header", "severity": "high", "status": "open", "summary": "x", "affected_asset": "a", "impact": "impact", "remediation": "fix", "cvss": 8.1},
        {"id": "2", "title": "Missing auth header", "severity": "high", "status": "open", "summary": "x", "affected_asset": "a", "impact": "impact", "remediation": "fix", "cvss": 8.1},
        {"id": "3", "title": "Info", "severity": "info", "status": "closed", "summary": "x", "affected_asset": "b"},
    ]
    report = FindingAnalytics(findings).report()
    assert report["risk_score"] == 14
    assert len(report["duplicate_groups"]) == 1
    assert report["remediation_queue"][0]["priority"] == 7


def test_scan_and_audit_analytics() -> None:
    scans = [{"target": "a", "status": "completed", "result": {"events": [{"check": "tls", "status": "finding", "severity": "medium"}]}}, {"target": "b", "status": "failed", "result": {"events": []}}]
    assert ScanAnalytics(scans).report()["finding_events"] == {"medium": 1}
    events = [{"action": "scan", "entity": "scan", "created_at": "2026-01-01"}, {"action": "scan", "entity": "finding", "created_at": "2026-01-02"}]
    assert AuditAnalytics(events).actions()["scan"] == 2


def test_inventory_with_known_executable() -> None:
    service = InventoryService((ToolSpec("python", "runtime", "python3", "runtime", "safe", ("python",)),))
    result = service.scan()
    assert result[0].installed
    assert service.summary(result)["total"] == 1


def test_redaction() -> None:
    assert "Bearer abc" not in redact_text("Authorization Bearer abc")
