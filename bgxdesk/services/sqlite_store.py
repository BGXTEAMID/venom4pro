"""SQLite persistence for the Kali Linux script mode.

The database is local-only and stores project metadata, not credentials. The
module exposes small repositories so scripts can use durable state without a
web server or external service.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
import hashlib
import json
import os
import sqlite3
import uuid


SCHEMA_VERSION = 1
DEFAULT_PATH = Path.home() / ".local" / "share" / "venom4pro" / "venom4pro.db"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id() -> str:
    return str(uuid.uuid4())


def pack(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def unpack(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


class SQLiteStore:
    def __init__(self, path: str | Path | None = None) -> None:
        env_path = os.getenv("VENOM4PRO_DB")
        self.path = Path(path or env_path or DEFAULT_PATH).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS authorizations (
                    id TEXT PRIMARY KEY,
                    client TEXT NOT NULL,
                    engagement TEXT NOT NULL,
                    reviewer TEXT NOT NULL,
                    start_at TEXT NOT NULL,
                    end_at TEXT NOT NULL,
                    emergency_contact TEXT NOT NULL,
                    approved_methods TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scope_rules (
                    id TEXT PRIMARY KEY,
                    authorization_id TEXT NOT NULL REFERENCES authorizations(id) ON DELETE CASCADE,
                    value TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    included INTEGER NOT NULL DEFAULT 1,
                    notes TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    owner TEXT NOT NULL DEFAULT '',
                    environment TEXT NOT NULL DEFAULT 'production',
                    tags TEXT NOT NULL DEFAULT '[]',
                    notes TEXT NOT NULL DEFAULT '',
                    in_scope INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS findings (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    affected_asset TEXT NOT NULL,
                    impact TEXT NOT NULL DEFAULT '',
                    remediation TEXT NOT NULL DEFAULT '',
                    references_json TEXT NOT NULL DEFAULT '[]',
                    evidence_ids TEXT NOT NULL DEFAULT '[]',
                    cvss REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS scans (
                    id TEXT PRIMARY KEY,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    finished_at TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    entity TEXT NOT NULL,
                    entity_id TEXT NOT NULL DEFAULT '',
                    details_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                INSERT OR IGNORE INTO metadata(key,value) VALUES ('schema_version','1');
                INSERT OR IGNORE INTO metadata(key,value) VALUES ('application','Venom4pro Kali Script Mode');
                """
            )
            conn.commit()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            conn.execute("BEGIN")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    def one(self, query: str, values: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.connect() as conn: return self.row(conn.execute(query, values).fetchone())

    def many(self, query: str, values: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as conn: return [dict(row) for row in conn.execute(query, values).fetchall()]

    def audit(self, action: str, entity: str, entity_id: str = "", details: dict[str, Any] | None = None) -> None:
        with self.connect() as conn:
            conn.execute("INSERT INTO audit_events VALUES (?,?,?,?,?,?)", (new_id(), action, entity, entity_id, pack(details or {}), now())); conn.commit()

    def add_authorization(self, record: dict[str, Any]) -> dict[str, Any]:
        record_id = new_id(); stamp = now()
        with self.transaction() as conn:
            conn.execute("UPDATE authorizations SET active=0")
            conn.execute("INSERT INTO authorizations VALUES (?,?,?,?,?,?,?,?,?,?)", (record_id, record["client"], record["engagement"], record["reviewer"], record["start_at"], record["end_at"], record["emergency_contact"], pack(record["approved_methods"]), 1, stamp))
            for rule in record["rules"]: conn.execute("INSERT INTO scope_rules VALUES (?,?,?,?,?,?)", (new_id(), record_id, rule["value"], rule.get("kind", "other"), int(rule.get("included", True)), rule.get("notes", "")))
        self.audit("authorization_created", "authorization", record_id, {"client": record["client"], "engagement": record["engagement"]}); return self.authorization(record_id) or {}

    def authorization(self, record_id: str | None = None) -> dict[str, Any] | None:
        query = "SELECT * FROM authorizations WHERE id=?" if record_id else "SELECT * FROM authorizations WHERE active=1 ORDER BY created_at DESC LIMIT 1"
        record = self.one(query, (record_id,) if record_id else ())
        if not record: return None
        record["approved_methods"] = unpack(record["approved_methods"], [])
        record["active"] = bool(record["active"])
        record["rules"] = self.many("SELECT id,value,kind,included,notes FROM scope_rules WHERE authorization_id=? ORDER BY value", (record["id"],))
        for rule in record["rules"]: rule["included"] = bool(rule["included"])
        return record

    def authorizations(self) -> list[dict[str, Any]]:
        records = self.many("SELECT id FROM authorizations ORDER BY created_at DESC")
        return [self.authorization(row["id"]) for row in records if self.authorization(row["id"])]

    def add_asset(self, asset: dict[str, Any], in_scope: bool) -> dict[str, Any]:
        asset_id = new_id(); stamp = now()
        with self.transaction() as conn: conn.execute("INSERT INTO assets VALUES (?,?,?,?,?,?,?,?,?,?)", (asset_id, asset["name"], asset.get("asset_type", "other"), asset.get("owner", ""), asset.get("environment", "production"), pack(asset.get("tags", [])), asset.get("notes", ""), int(in_scope), stamp, stamp))
        self.audit("asset_created", "asset", asset_id, {"name": asset["name"], "in_scope": in_scope}); return self.asset(asset_id) or {}

    def asset(self, asset_id: str) -> dict[str, Any] | None:
        value = self.one("SELECT * FROM assets WHERE id=?", (asset_id,))
        if value: value["tags"] = unpack(value["tags"], []); value["in_scope"] = bool(value["in_scope"])
        return value

    def assets(self, query: str = "") -> list[dict[str, Any]]:
        rows = self.many("SELECT * FROM assets WHERE name LIKE ? ORDER BY updated_at DESC", (f"%{query}%",)) if query else self.many("SELECT * FROM assets ORDER BY updated_at DESC")
        for value in rows: value["tags"] = unpack(value["tags"], []); value["in_scope"] = bool(value["in_scope"])
        return rows

    def add_finding(self, finding: dict[str, Any]) -> dict[str, Any]:
        finding_id = new_id(); stamp = now()
        with self.transaction() as conn: conn.execute("INSERT INTO findings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (finding_id, finding["title"], finding["severity"], finding.get("status", "draft"), finding["summary"], finding["affected_asset"], finding.get("impact", ""), finding.get("remediation", ""), pack(finding.get("references", [])), pack(finding.get("evidence_ids", [])), finding.get("cvss"), stamp, stamp))
        self.audit("finding_created", "finding", finding_id, {"title": finding["title"], "severity": finding["severity"]}); return self.finding(finding_id) or {}

    def finding(self, finding_id: str) -> dict[str, Any] | None:
        value = self.one("SELECT * FROM findings WHERE id=?", (finding_id,))
        if value: value["references"] = unpack(value.pop("references_json"), []); value["evidence_ids"] = unpack(value["evidence_ids"], [])
        return value

    def findings(self, status: str | None = None, severity: str | None = None) -> list[dict[str, Any]]:
        clauses = []; values: list[Any] = []
        if status: clauses.append("status=?"); values.append(status)
        if severity: clauses.append("severity=?"); values.append(severity)
        sql = "SELECT * FROM findings" + (" WHERE " + " AND ".join(clauses) if clauses else "") + " ORDER BY created_at DESC"
        rows = self.many(sql, tuple(values))
        for value in rows: value["references"] = unpack(value.pop("references_json"), []); value["evidence_ids"] = unpack(value["evidence_ids"], [])
        return rows

    def transition_finding(self, finding_id: str, status: str) -> dict[str, Any]:
        current = self.finding(finding_id)
        if not current: raise KeyError(finding_id)
        allowed = {"draft": {"open"}, "open": {"accepted", "remediated", "closed"}, "accepted": {"remediated", "closed"}, "remediated": {"verified", "open"}, "verified": {"closed", "open"}, "closed": {"open"}}
        if status not in allowed.get(current["status"], set()): raise ValueError(f"invalid transition {current['status']} -> {status}")
        self.execute("UPDATE findings SET status=?,updated_at=? WHERE id=?", (status, now(), finding_id)); self.audit("finding_transition", "finding", finding_id, {"from": current["status"], "to": status}); return self.finding(finding_id) or {}

    def execute(self, query: str, values: tuple[Any, ...] = ()) -> None:
        with self.connect() as conn: conn.execute(query, values); conn.commit()

    def add_evidence(self, title: str, content: str, source: str) -> dict[str, Any]:
        evidence_id = new_id(); stamp = now(); checksum = hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()
        with self.transaction() as conn: conn.execute("INSERT INTO evidence VALUES (?,?,?,?,?,?)", (evidence_id, title, content, source, checksum, stamp))
        self.audit("evidence_created", "evidence", evidence_id, {"source": source}); return {"id": evidence_id, "title": title, "content": content, "source": source, "checksum": checksum, "created_at": stamp}

    def add_scan(self, target: str, result: dict[str, Any], error: str = "") -> dict[str, Any]:
        scan_id = new_id(); stamp = now(); finished = now(); payload = pack(result)
        with self.transaction() as conn: conn.execute("INSERT INTO scans VALUES (?,?,?,?,?,?,?)", (scan_id, target, result.get("status", "completed"), payload, error, stamp, finished))
        evidence = self.add_evidence(f"Automatic scan: {target}", payload, "sqlite-read-only-scanner"); self.audit("scan_completed", "scan", scan_id, {"target": target, "evidence_id": evidence["id"]}); return {"id": scan_id, "target": target, "status": result.get("status", "completed"), "result": result, "evidence_id": evidence["id"], "created_at": stamp, "finished_at": finished}

    def scans(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.many("SELECT * FROM scans ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 500)),))
        for row in rows: row["result"] = unpack(row.pop("result_json"), {})
        return rows

    def audit_events(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self.many("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?", (max(1, min(limit, 1000)),))
        for row in rows: row["details"] = unpack(row.pop("details_json"), {})
        return rows

    def status(self) -> dict[str, Any]:
        counts = {}
        for table in ("authorizations", "assets", "findings", "evidence", "scans", "audit_events"): counts[table] = int(self.one(f"SELECT COUNT(*) AS count FROM {table}")["count"])
        severity = {name: len(self.findings(severity=name)) for name in ("info", "low", "medium", "high", "critical")}
        return {"database": str(self.path), "schema_version": SCHEMA_VERSION, "counts": counts, "finding_by_severity": severity, "active_authorization": bool(self.authorization())}
