"""Append-only local safety journal for operator-visible decisions."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import os
import uuid


class SafetyJournal:
    def __init__(self, path: str | Path) -> None: self.path = Path(path).expanduser().resolve(); self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def timestamp() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def append(self, action: str, outcome: str, details: dict[str, Any] | None = None, actor: str = "local-user") -> dict[str, Any]:
        previous = self.last_hash(); event = {"id": str(uuid.uuid4()), "created_at": self.timestamp(), "action": action, "outcome": outcome, "actor": actor, "details": details or {}, "previous_hash": previous}; payload = json.dumps(event, sort_keys=True, ensure_ascii=False); event["hash"] = hashlib.sha256(payload.encode()).hexdigest();
        with self.path.open("a", encoding="utf-8") as handle: handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
        return event

    def entries(self) -> list[dict[str, Any]]:
        if not self.path.exists(): return []
        values = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try: values.append(json.loads(line))
            except json.JSONDecodeError: continue
        return values

    def last_hash(self) -> str: values = self.entries(); return values[-1].get("hash", "") if values else ""

    def verify(self) -> dict[str, Any]:
        values = self.entries(); previous = ""; invalid = []
        for index, event in enumerate(values):
            if event.get("previous_hash", "") != previous: invalid.append({"index": index, "reason": "previous hash mismatch"})
            copy = dict(event); stored = copy.pop("hash", ""); payload = json.dumps(copy, sort_keys=True, ensure_ascii=False); actual = hashlib.sha256(payload.encode()).hexdigest()
            if stored != actual: invalid.append({"index": index, "reason": "content hash mismatch"})
            previous = stored
        return {"ok": not invalid, "entries": len(values), "invalid": invalid}

    def export(self, destination: str | Path) -> Path:
        destination = Path(destination).expanduser().resolve(); destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text("\n".join(json.dumps(entry, ensure_ascii=False, sort_keys=True) for entry in self.entries()) + ("\n" if self.entries() else ""), encoding="utf-8"); return destination
