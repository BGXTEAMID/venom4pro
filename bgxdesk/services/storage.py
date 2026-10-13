"""Offline JSON persistence with atomic writes and lightweight migrations."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, TypeVar, Callable
import json
import os
import shutil
import tempfile

from bgxdesk.domain.models import (
    Asset, AssetType, AuditEvent, AuthorizationRecord, Evidence, Finding,
    FindingStatus, Policy, ProjectSnapshot, ScopeRule, Severity, ToolRecord,
)

T = TypeVar("T")
SCHEMA_VERSION = 2


class StorageError(RuntimeError):
    """Raised when the local project store cannot be read or written."""


class JsonStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.backup_path = self.path.with_suffix(self.path.suffix + ".bak")

    def exists(self) -> bool:
        return self.path.exists()

    def read_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.empty_document()
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                raw = json.load(handle)
            if not isinstance(raw, dict):
                raise StorageError("Project document must be an object")
            return self.migrate(raw)
        except json.JSONDecodeError as exc:
            raise StorageError(f"Invalid project JSON: {exc}") from exc
        except OSError as exc:
            raise StorageError(f"Unable to read project: {exc}") from exc

    def write_raw(self, document: dict[str, Any]) -> None:
        document = self.migrate(document)
        payload = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        temporary: Path | None = None
        try:
            if self.path.exists():
                shutil.copy2(self.path, self.backup_path)
            fd, name = tempfile.mkstemp(prefix=".bgxdesk-", suffix=".json", dir=self.path.parent)
            temporary = Path(name)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            if temporary and temporary.exists():
                temporary.unlink(missing_ok=True)
            raise StorageError(f"Unable to write project: {exc}") from exc

    @staticmethod
    def empty_document() -> dict[str, Any]:
        return {"schema_version": SCHEMA_VERSION, "meta": {"application": "BGXTEAM Security Desk"}, "authorizations": [], "assets": [], "findings": [], "evidence": [], "events": [], "tools": []}

    @staticmethod
    def migrate(document: dict[str, Any]) -> dict[str, Any]:
        version = int(document.get("schema_version", 1))
        result = dict(document)
        for key in ("authorizations", "assets", "findings", "evidence", "events", "tools"):
            if not isinstance(result.get(key), list):
                result[key] = []
        if version < 2:
            result.setdefault("meta", {})
            result["meta"]["migrated_from"] = version
            result["schema_version"] = 2
        else:
            result["schema_version"] = SCHEMA_VERSION
        return result

    def load(self) -> ProjectSnapshot:
        raw = self.read_raw()
        return snapshot_from_dict(raw)

    def save(self, snapshot: ProjectSnapshot) -> None:
        document = snapshot_to_dict(snapshot)
        document["schema_version"] = SCHEMA_VERSION
        document["meta"] = {"application": "BGXTEAM Security Desk", "counts": snapshot.counts()}
        self.write_raw(document)

    def restore_backup(self) -> None:
        if not self.backup_path.exists():
            raise StorageError("No backup is available")
        shutil.copy2(self.backup_path, self.path)


class Repository:
    def __init__(self, store: JsonStore) -> None:
        self.store = store
        self.snapshot = store.load()

    def reload(self) -> ProjectSnapshot:
        self.snapshot = self.store.load()
        return self.snapshot

    def save(self) -> None:
        self.store.save(self.snapshot)

    def add(self, collection: str, value: Any) -> Any:
        values = getattr(self.snapshot, collection)
        values.append(value)
        self.save()
        return value

    def update(self, collection: str, identifier: str, updater: Callable[[Any], Any]) -> Any:
        value = self.get(collection, identifier)
        if value is None:
            raise KeyError(f"No {collection} record with id {identifier}")
        result = updater(value)
        self.save()
        return result or value

    def delete(self, collection: str, identifier: str) -> bool:
        values = getattr(self.snapshot, collection)
        before = len(values)
        values[:] = [item for item in values if getattr(item, "id", None) != identifier]
        changed = len(values) != before
        if changed:
            self.save()
        return changed

    def get(self, collection: str, identifier: str) -> Any | None:
        return next((item for item in getattr(self.snapshot, collection) if getattr(item, "id", None) == identifier), None)

    def list(self, collection: str) -> list[Any]:
        return list(getattr(self.snapshot, collection))

    def search_findings(self, query: str) -> list[Finding]:
        text = query.strip().lower()
        if not text:
            return list(self.snapshot.findings)
        return [item for item in self.snapshot.findings if text in " ".join((item.title, item.summary, item.affected_asset, item.status.value, item.severity.value)).lower()]

    def append_event(self, event: AuditEvent) -> None:
        self.snapshot.events.append(event)
        self.save()


def snapshot_to_dict(snapshot: ProjectSnapshot) -> dict[str, Any]:
    def encode(value: Any) -> Any:
        if hasattr(value, "value"):
            return value.value
        if hasattr(value, "__dataclass_fields__"):
            return {key: encode(item) for key, item in asdict(value).items()}
        if isinstance(value, list):
            return [encode(item) for item in value]
        if isinstance(value, dict):
            return {key: encode(item) for key, item in value.items()}
        return value
    return {key: encode(getattr(snapshot, key)) for key in ("authorizations", "assets", "findings", "evidence", "events", "tools")}


def snapshot_from_dict(data: dict[str, Any]) -> ProjectSnapshot:
    authorizations = []
    for item in data.get("authorizations", []):
        try:
            authorizations.append(AuthorizationRecord.from_dict(item))
        except (TypeError, ValueError):
            continue
    assets = [Asset(name=item.get("name", ""), asset_type=enum_or(AssetType, item.get("asset_type"), AssetType.OTHER), owner=item.get("owner", ""), environment=item.get("environment", "production"), tags=list(item.get("tags", [])), notes=item.get("notes", ""), id=item.get("id", ""), created_at=item.get("created_at", ""), updated_at=item.get("updated_at", ""), in_scope=bool(item.get("in_scope", False))) for item in data.get("assets", [])]
    findings = [Finding(title=item.get("title", ""), severity=enum_or(Severity, item.get("severity"), Severity.INFO), summary=item.get("summary", ""), affected_asset=item.get("affected_asset", ""), reproduction=item.get("reproduction", ""), impact=item.get("impact", ""), remediation=item.get("remediation", ""), references=list(item.get("references", [])), evidence_ids=list(item.get("evidence_ids", [])), status=enum_or(FindingStatus, item.get("status"), FindingStatus.DRAFT), cvss=item.get("cvss"), assignee=item.get("assignee", ""), id=item.get("id", ""), created_at=item.get("created_at", ""), updated_at=item.get("updated_at", "")) for item in data.get("findings", [])]
    evidence = [Evidence(title=item.get("title", ""), content=item.get("content", ""), source=item.get("source", "manual"), checksum=item.get("checksum", ""), id=item.get("id", ""), created_at=item.get("created_at", "")) for item in data.get("evidence", [])]
    events = [AuditEvent(action=item.get("action", ""), entity=item.get("entity", ""), entity_id=item.get("entity_id", ""), actor=item.get("actor", "local-user"), details=dict(item.get("details", {})), created_at=item.get("created_at", ""), id=item.get("id", "")) for item in data.get("events", [])]
    tools = [ToolRecord(name=item.get("name", ""), category=item.get("category", ""), purpose=item.get("purpose", ""), executable=item.get("executable", ""), policy=enum_or(Policy, item.get("policy"), Policy.REVIEW), aliases=list(item.get("aliases", [])), documentation_url=item.get("documentation_url", ""), installed=bool(item.get("installed", False)), version=item.get("version", ""), last_checked=item.get("last_checked", "")) for item in data.get("tools", [])]
    return ProjectSnapshot(authorizations=authorizations, assets=assets, findings=findings, evidence=evidence, events=events, tools=tools)


def enum_or(enum_type: type[T], value: Any, fallback: T) -> T:
    try:
        return enum_type(value)
    except (ValueError, TypeError):
        return fallback
