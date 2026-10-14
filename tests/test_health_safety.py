from pathlib import Path
from tempfile import TemporaryDirectory

from bgxdesk.services.health import HealthService
from bgxdesk.services.safety_log import SafetyJournal
from bgxdesk.services.sqlite_store import SQLiteStore


def test_health_service() -> None:
    with TemporaryDirectory() as folder:
        result = HealthService(SQLiteStore(Path(folder) / "db.sqlite")).run()
        assert result["ok"]
        assert {item["name"] for item in result["checks"]} == {"database", "storage", "policy", "python"}


def test_safety_journal_chain() -> None:
    with TemporaryDirectory() as folder:
        journal = SafetyJournal(Path(folder) / "safety.jsonl")
        journal.append("scope-check", "allowed", {"target": "localhost"})
        journal.append("scan", "completed", {"events": 3})
        assert journal.verify()["ok"]
        assert len(journal.entries()) == 2
