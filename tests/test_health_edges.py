from pathlib import Path
from tempfile import TemporaryDirectory

from bgxdesk.services.health import HealthService
from bgxdesk.services.safety_log import SafetyJournal
from bgxdesk.services.sqlite_store import SQLiteStore


def test_health_database_and_storage_checks() -> None:
    with TemporaryDirectory() as folder:
        store = SQLiteStore(Path(folder) / "state.db")
        service = HealthService(store)
        database = service.check_database()
        storage = service.check_storage()
        assert database.ok is True
        assert storage.ok is True
        assert database.details["path"].endswith("state.db")


def test_safety_journal_export() -> None:
    with TemporaryDirectory() as folder:
        journal = SafetyJournal(Path(folder) / "safety.jsonl")
        journal.append("policy", "allowed", {"scope": "local"})
        destination = journal.export(Path(folder) / "export.jsonl")
        assert destination.exists()
        assert destination.read_text(encoding="utf-8").count("policy") == 1
        assert journal.verify()["invalid"] == []
