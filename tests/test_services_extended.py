from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from bgxdesk.services.policy import DataPolicy, FindingPolicy, OperationPolicy, ScopePolicy, validate_operation
from bgxdesk.services.project_ops import ProjectMaintenance
from bgxdesk.services.reporting import ReportBuilder
from bgxdesk.services.sqlite_store import SQLiteStore


def make_record(value: str = "example.com") -> dict:
    return {"client": "Client", "engagement": "Engagement", "reviewer": "Reviewer", "start_at": "start", "end_at": "end", "emergency_contact": "contact", "approved_methods": ["read-only"], "rules": [{"value": value, "kind": "domain", "included": True}]}


def test_scope_policy_wildcard_and_exclusion() -> None:
    policy = ScopePolicy([{"value": "*.example.com", "included": True}, {"value": "admin.example.com", "included": False}])
    assert policy.explain("https://app.example.com").allowed
    assert not policy.explain("https://admin.example.com").allowed


def test_operation_policy_rejects_dangerous_method() -> None:
    result = OperationPolicy().validate_scan("https://example.com", 5, 1, 10000, "POST")
    assert not result.allowed


def test_finding_policy_requires_impact() -> None:
    errors = FindingPolicy().validate({"title": "x", "severity": "critical", "summary": "x", "affected_asset": "x"})
    assert "impact is required for critical findings" in errors


def test_data_policy_redacts_tokens() -> None:
    value = DataPolicy().redact({"Authorization": "Bearer abc", "nested": "token=secret"})
    assert value["Authorization"] == "[REDACTED]"
    assert "REDACTED" in value["nested"]


def test_backup_export_import_and_report() -> None:
    with TemporaryDirectory() as folder:
        root = Path(folder); store = SQLiteStore(root / "project.db"); store.add_authorization(make_record()); store.add_asset({"name": "app.example.com", "asset_type": "domain"}, True); store.add_finding({"title": "Header", "severity": "low", "summary": "Summary", "affected_asset": "app.example.com"})
        maintenance = ProjectMaintenance(store); assert maintenance.integrity_check()["ok"]
        backup = maintenance.backup(root / "backup.db"); assert Path(backup["path"]).exists()
        export_path = maintenance.export_json(root / "export.json"); assert export_path.exists()
        report = ReportBuilder(store).write(root / "report.md"); assert "Header" in report.read_text(encoding="utf-8")
        other = SQLiteStore(root / "other.db"); imported = ProjectMaintenance(other).import_json(export_path); assert imported["findings"] == 1


def test_validate_operation_requires_scope() -> None:
    report = validate_operation("https://outside.invalid", [{"value": "example.com", "included": True}], 5, 1, 10000)
    assert not report.allowed
