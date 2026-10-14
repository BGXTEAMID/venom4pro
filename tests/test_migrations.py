from pathlib import Path
from tempfile import TemporaryDirectory

from bgxdesk.services.migrations import MigrationManager
from bgxdesk.services.sqlite_store import SQLiteStore


def test_migration_manager() -> None:
    with TemporaryDirectory() as folder:
        root = Path(folder); migrations = root / "migrations"; migrations.mkdir(); (migrations / "001_baseline.sql").write_text("CREATE TABLE IF NOT EXISTS note (id TEXT);", encoding="utf-8")
        manager = MigrationManager(SQLiteStore(root / "db.sqlite"), migrations); assert manager.status()["available"] == [1]; result = manager.apply(); assert result["applied"][0]["status"] == "applied"; assert manager.verify()["ok"]
