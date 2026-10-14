"""Evidence handling with checksums and local chain-of-custody metadata."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import mimetypes
import os
import shutil
import uuid

from bgxdesk.services.policy import DataPolicy
from bgxdesk.services.sqlite_store import SQLiteStore, now


@dataclass
class EvidenceItem:
    id: str
    title: str
    source: str
    content_type: str
    size: int
    checksum: str
    created_at: str
    path: str = ""
    redacted: bool = False

    def as_dict(self) -> dict[str, Any]: return asdict(self)


class EvidenceService:
    def __init__(self, store: SQLiteStore, root: str | Path | None = None) -> None:
        self.store = store; self.root = Path(root or (Path.home() / ".local/share/venom4pro/evidence")).expanduser().resolve(); self.root.mkdir(parents=True, exist_ok=True); self.policy = DataPolicy()

    @staticmethod
    def checksum_bytes(content: bytes) -> str: return hashlib.sha256(content).hexdigest()

    def add_text(self, title: str, content: str, source: str = "manual", redact: bool = True) -> EvidenceItem:
        errors = self.policy.validate_evidence(title, content)
        if errors: raise ValueError("; ".join(errors))
        safe_content = self.policy.redact(content) if redact else content; item_id = str(uuid.uuid4()); payload = safe_content.encode("utf-8"); checksum = self.checksum_bytes(payload); filename = self.root / f"{item_id}.txt"; filename.write_bytes(payload); record = self.store.add_evidence(title, safe_content, source); return EvidenceItem(record["id"], title, source, "text/plain", len(payload), checksum, record["created_at"], str(filename), redact)

    def add_file(self, title: str, path: str | Path, source: str = "file", max_bytes: int = 10_000_000) -> EvidenceItem:
        source_path = Path(path).expanduser().resolve()
        if not source_path.is_file(): raise FileNotFoundError(source_path)
        if source_path.stat().st_size > max_bytes: raise ValueError("file exceeds evidence size limit")
        payload = source_path.read_bytes(); item_id = str(uuid.uuid4()); destination = self.root / f"{item_id}-{source_path.name}"; shutil.copy2(source_path, destination); checksum = self.checksum_bytes(payload); content = f"File: {source_path}\nSize: {len(payload)} bytes\nSHA256: {checksum}\nStored: {destination}\n"; record = self.store.add_evidence(title, content, source); return EvidenceItem(record["id"], title, source, mimetypes.guess_type(source_path.name)[0] or "application/octet-stream", len(payload), checksum, record["created_at"], str(destination), False)

    def manifest(self) -> list[dict[str, Any]]:
        rows = self.store.many("SELECT id,title,source,checksum,created_at FROM evidence ORDER BY created_at DESC")
        return rows

    def verify(self, item_id: str) -> dict[str, Any]:
        record = self.store.one("SELECT * FROM evidence WHERE id=?", (item_id,))
        if not record: raise KeyError(item_id)
        content = record["content"].encode("utf-8"); actual = self.checksum_bytes(content); return {"id": item_id, "stored_checksum": record["checksum"], "calculated_checksum": actual, "match": actual == record["checksum"], "created_at": record["created_at"]}

    def verify_all(self) -> dict[str, Any]:
        items = self.manifest(); results = []
        for item in items:
            try: results.append(self.verify(item["id"]))
            except KeyError: results.append({"id": item["id"], "match": False, "error": "missing"})
        return {"total": len(results), "valid": sum(item.get("match") is True for item in results), "invalid": sum(item.get("match") is not True for item in results), "items": results}

    def attach_to_finding(self, finding_id: str, evidence_id: str) -> dict[str, Any]:
        finding = self.store.finding(finding_id)
        if not finding: raise KeyError(finding_id)
        evidence = self.store.one("SELECT id FROM evidence WHERE id=?", (evidence_id,))
        if not evidence: raise KeyError(evidence_id)
        ids = list(finding.get("evidence_ids", []));
        if evidence_id not in ids: ids.append(evidence_id)
        self.store.execute("UPDATE findings SET evidence_ids=?,updated_at=? WHERE id=?", (json.dumps(ids), now(), finding_id)); self.store.audit("evidence_attached", "finding", finding_id, {"evidence_id": evidence_id}); return self.store.finding(finding_id) or {}
