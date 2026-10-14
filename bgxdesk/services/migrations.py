"""Versioned local SQLite migration helper."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import hashlib
import re

from bgxdesk.services.sqlite_store import SQLiteStore, now


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str
    checksum: str

    @classmethod
    def create(cls, version: int, name: str, sql: str) -> "Migration": return cls(version, name, sql, hashlib.sha256(sql.encode()).hexdigest())


class MigrationManager:
    def __init__(self, store: SQLiteStore, directory: str | Path | None = None) -> None:
        self.store = store; self.directory = Path(directory or (Path(__file__).resolve().parents[2] / "migrations")).resolve()

    def discover(self) -> list[Migration]:
        migrations = []
        for path in sorted(self.directory.glob("*.sql")):
            match = re.match(r"^(\d+)[_-](.+)\.sql$", path.name)
            if match: migrations.append(Migration.create(int(match.group(1)), match.group(2), path.read_text(encoding="utf-8")))
        return sorted(migrations, key=lambda item: item.version)

    def applied(self) -> list[dict]: return self.store.many("SELECT key,value FROM metadata WHERE key LIKE 'migration:%' ORDER BY key")

    def apply(self) -> dict:
        applied = {int(item["key"].split(":", 1)[1]): item["value"] for item in self.applied()}; result = []
        for migration in self.discover():
            if migration.version in applied:
                result.append({"version": migration.version, "status": "already-applied", "checksum": applied[migration.version]}); continue
            with self.store.transaction() as conn: conn.executescript(migration.sql); conn.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES (?,?)", (f"migration:{migration.version}", migration.checksum))
            result.append({"version": migration.version, "status": "applied", "checksum": migration.checksum})
        self.store.audit("migrations_applied", "database", details={"result": result}); return {"applied": result, "current": max((item.version for item in self.discover()), default=0)}

    def verify(self) -> dict:
        stored = {int(item["key"].split(":", 1)[1]): item["value"] for item in self.applied()}; checks = []
        for migration in self.discover(): checks.append({"version": migration.version, "name": migration.name, "expected": migration.checksum, "actual": stored.get(migration.version), "match": stored.get(migration.version) == migration.checksum})
        return {"ok": all(item["match"] for item in checks), "checks": checks}

    def status(self) -> dict: return {"directory": str(self.directory), "available": [migration.version for migration in self.discover()], "applied": [item["key"] for item in self.applied()], "verification": self.verify()}
