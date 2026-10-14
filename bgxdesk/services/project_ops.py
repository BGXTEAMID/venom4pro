"""Project maintenance helpers for the SQLite script mode."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import shutil
import sqlite3
import tempfile

from bgxdesk.services.sqlite_store import SQLiteStore, now, pack, unpack


class ProjectOperationError(RuntimeError): pass


class ProjectMaintenance:
    def __init__(self, store: SQLiteStore) -> None: self.store = store

    def checksum(self, path: str | Path | None = None) -> str:
        target = Path(path or self.store.path)
        if not target.exists(): raise ProjectOperationError(f"file does not exist: {target}")
        digest = hashlib.sha256()
        with target.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""): digest.update(block)
        return digest.hexdigest()

    def backup(self, destination: str | Path) -> dict[str, Any]:
        destination = Path(destination).expanduser().resolve(); destination.parent.mkdir(parents=True, exist_ok=True)
        if destination == self.store.path: raise ProjectOperationError("backup destination cannot equal active database")
        with self.store.connect() as source, sqlite3.connect(destination) as target:
            source.backup(target)
        checksum = self.checksum(destination); self.store.audit("database_backup", "database", details={"path": str(destination), "checksum": checksum})
        return {"path": str(destination), "checksum": checksum, "created_at": now()}

    def restore(self, source: str | Path, create_backup: bool = True) -> dict[str, Any]:
        source = Path(source).expanduser().resolve()
        if not source.exists(): raise ProjectOperationError(f"backup does not exist: {source}")
        if source == self.store.path: raise ProjectOperationError("source is already active database")
        validation = SQLiteStore(source).status()
        previous = ""
        if create_backup and self.store.path.exists(): previous = str(self.backup(self.store.path.with_suffix(".before-restore.db"))["path"])
        temporary = self.store.path.with_suffix(".restore.tmp")
        shutil.copy2(source, temporary); temporary.replace(self.store.path)
        self.store.initialize(); self.store.audit("database_restore", "database", details={"source": str(source), "previous_backup": previous, "validation": validation})
        return {"restored_from": str(source), "previous_backup": previous, "status": self.store.status()}

    def export_json(self, destination: str | Path) -> Path:
        destination = Path(destination).expanduser().resolve(); destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {"exported_at": now(), "schema_version": 1, "status": self.store.status(), "authorizations": self.store.authorizations(), "assets": self.store.assets(), "findings": self.store.findings(), "scans": self.store.scans(), "audit_events": self.store.audit_events(10000)}
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"); self.store.audit("project_export", "project", details={"path": str(destination), "checksum": self.checksum(destination)}); return destination

    def import_json(self, source: str | Path, replace: bool = False) -> dict[str, Any]:
        source = Path(source).expanduser().resolve()
        try: payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc: raise ProjectOperationError(str(exc)) from exc
        required = {"authorizations", "assets", "findings"}
        missing = required - set(payload)
        if missing: raise ProjectOperationError(f"import missing sections: {sorted(missing)}")
        imported = {"authorizations": 0, "assets": 0, "findings": 0, "scans": 0}
        with self.store.transaction() as conn:
            if replace:
                for table in ("scope_rules", "authorizations", "assets", "findings", "evidence", "scans", "audit_events"): conn.execute(f"DELETE FROM {table}")
            for record in payload.get("authorizations", []):
                existing = conn.execute("SELECT 1 FROM authorizations WHERE id=?", (record.get("id"),)).fetchone()
                if existing: continue
                conn.execute("INSERT INTO authorizations VALUES (?,?,?,?,?,?,?,?,?,?)", (record["id"], record["client"], record["engagement"], record["reviewer"], record["start_at"], record["end_at"], record["emergency_contact"], pack(record.get("approved_methods", [])), int(record.get("active", False)), record.get("created_at", now())))
                for rule in record.get("rules", []): conn.execute("INSERT INTO scope_rules VALUES (?,?,?,?,?,?)", (rule.get("id"), record["id"], rule["value"], rule.get("kind", "other"), int(rule.get("included", True)), rule.get("notes", "")))
                imported["authorizations"] += 1
            for record in payload.get("assets", []):
                if conn.execute("SELECT 1 FROM assets WHERE id=?", (record.get("id"),)).fetchone(): continue
                conn.execute("INSERT INTO assets VALUES (?,?,?,?,?,?,?,?,?,?)", (record["id"], record["name"], record.get("asset_type", "other"), record.get("owner", ""), record.get("environment", "production"), pack(record.get("tags", [])), record.get("notes", ""), int(record.get("in_scope", False)), record.get("created_at", now()), record.get("updated_at", now()))); imported["assets"] += 1
            for record in payload.get("findings", []):
                if conn.execute("SELECT 1 FROM findings WHERE id=?", (record.get("id"),)).fetchone(): continue
                conn.execute("INSERT INTO findings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (record["id"], record["title"], record["severity"], record.get("status", "draft"), record["summary"], record["affected_asset"], record.get("impact", ""), record.get("remediation", ""), pack(record.get("references", [])), pack(record.get("evidence_ids", [])), record.get("cvss"), record.get("created_at", now()), record.get("updated_at", now()))); imported["findings"] += 1
        self.store.audit("project_import", "project", details={"source": str(source), "replace": replace, "imported": imported}); return imported

    def vacuum(self) -> dict[str, Any]:
        with self.store.connect() as conn: before = conn.execute("PRAGMA page_count").fetchone()[0]; conn.execute("VACUUM"); after = conn.execute("PRAGMA page_count").fetchone()[0]
        self.store.audit("database_vacuum", "database", details={"pages_before": before, "pages_after": after}); return {"pages_before": before, "pages_after": after}

    def integrity_check(self) -> dict[str, Any]:
        with self.store.connect() as conn: result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        return {"ok": result == "ok", "result": result, "database": str(self.store.path), "checksum": self.checksum()}
