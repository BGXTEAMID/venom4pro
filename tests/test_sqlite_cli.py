from pathlib import Path
from tempfile import TemporaryDirectory

from bgxdesk.services.sqlite_store import SQLiteStore


def test_sqlite_lifecycle() -> None:
    with TemporaryDirectory() as folder:
        store = SQLiteStore(Path(folder) / "assessment.db")
        record = store.add_authorization({"client": "Lab", "engagement": "Test", "reviewer": "QA", "start_at": "now", "end_at": "later", "emergency_contact": "local", "approved_methods": ["read-only"], "rules": [{"value": "127.0.0.1", "kind": "ip", "included": True}]})
        assert record["active"] is True
        asset = store.add_asset({"name": "127.0.0.1", "asset_type": "ip"}, True)
        assert asset["in_scope"] is True
        finding = store.add_finding({"title": "Header", "severity": "low", "summary": "Missing header", "affected_asset": asset["name"]})
        assert store.transition_finding(finding["id"], "open")["status"] == "open"
        scan = store.add_scan("http://127.0.0.1", {"status": "completed", "events": []})
        assert store.scans()[0]["id"] == scan["id"]
        assert store.status()["counts"]["audit_events"] >= 4
