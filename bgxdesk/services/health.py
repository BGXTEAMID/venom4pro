"""Local readiness and health checks; no network probes are performed."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Callable
import os
import shutil
import sqlite3

from bgxdesk.services.inventory import EnvironmentDoctor
from bgxdesk.services.policy import OperationPolicy
from bgxdesk.services.sqlite_store import SQLiteStore


@dataclass
class HealthCheck:
    name: str
    ok: bool
    message: str
    details: dict[str, Any]

    def as_dict(self) -> dict[str, Any]: return asdict(self)


class HealthService:
    def __init__(self, store: SQLiteStore) -> None: self.store = store

    def check_database(self) -> HealthCheck:
        try:
            with self.store.connect() as conn: result = conn.execute("PRAGMA integrity_check").fetchone()[0]
            return HealthCheck("database", result == "ok", result, {"path": str(self.store.path), "size": self.store.path.stat().st_size if self.store.path.exists() else 0})
        except sqlite3.Error as exc: return HealthCheck("database", False, str(exc), {})

    def check_storage(self) -> HealthCheck:
        path = self.store.path.parent; usable = shutil.disk_usage(path).free; ok = path.exists() and os.access(path, os.W_OK) and usable > 10 * 1024 * 1024; return HealthCheck("storage", ok, "writable storage available" if ok else "storage is not writable or has less than 10MB free", {"path": str(path), "free_bytes": usable})

    def check_policy(self) -> HealthCheck:
        result = OperationPolicy().validate_scan("http://127.0.0.1", 8, 0.6, 512000); return HealthCheck("policy", result.allowed, result.reason, {"warnings": result.warnings})

    def check_python(self) -> HealthCheck:
        data = EnvironmentDoctor().python(); return HealthCheck("python", bool(data.get("version")), data.get("version", "unknown"), data)

    def run(self) -> dict[str, Any]:
        checks = [self.check_database(), self.check_storage(), self.check_policy(), self.check_python()]; return {"ok": all(check.ok for check in checks), "checks": [check.as_dict() for check in checks]}
