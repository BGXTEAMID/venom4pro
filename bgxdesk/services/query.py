"""Read-only query helpers for SQLite-backed CLI workflows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
import re

from bgxdesk.services.sqlite_store import SQLiteStore


@dataclass(frozen=True)
class Page:
    items: list[dict[str, Any]]
    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int: return (self.total + self.page_size - 1) // self.page_size if self.page_size else 0

    def as_dict(self) -> dict[str, Any]: return {"items": self.items, "page": self.page, "page_size": self.page_size, "total": self.total, "pages": self.pages}


class ProjectQuery:
    def __init__(self, store: SQLiteStore) -> None: self.store = store

    @staticmethod
    def normalize_query(value: str) -> str: return re.sub(r"\s+", " ", value.strip().lower())

    @staticmethod
    def paginate(items: Iterable[dict[str, Any]], page: int = 1, page_size: int = 25) -> Page:
        values = list(items); page = max(1, page); page_size = max(1, min(page_size, 500)); start = (page - 1) * page_size; return Page(values[start:start + page_size], page, page_size, len(values))

    def find_findings(self, query: str = "", severity: str | None = None, status: str | None = None, page: int = 1, page_size: int = 25) -> Page:
        text = self.normalize_query(query); values = self.store.findings(status=status, severity=severity)
        if text: values = [item for item in values if text in " ".join(str(item.get(key, "")) for key in ("title", "summary", "affected_asset", "impact", "remediation")).lower()]
        return self.paginate(values, page, page_size)

    def find_assets(self, query: str = "", environment: str | None = None, in_scope: bool | None = None, page: int = 1, page_size: int = 25) -> Page:
        text = self.normalize_query(query); values = self.store.assets()
        if text: values = [item for item in values if text in " ".join(str(item.get(key, "")) for key in ("name", "owner", "environment", "notes")).lower()]
        if environment: values = [item for item in values if item.get("environment") == environment]
        if in_scope is not None: values = [item for item in values if item.get("in_scope") is in_scope]
        return self.paginate(values, page, page_size)

    def find_events(self, query: str = "", action: str | None = None, entity: str | None = None, page: int = 1, page_size: int = 50) -> Page:
        text = self.normalize_query(query); values = self.store.audit_events(1000)
        if action: values = [item for item in values if item.get("action") == action]
        if entity: values = [item for item in values if item.get("entity") == entity]
        if text: values = [item for item in values if text in str(item).lower()]
        return self.paginate(values, page, page_size)

    def environment_values(self) -> list[str]: return sorted({item.get("environment", "") for item in self.store.assets() if item.get("environment")})

    def asset_names(self) -> list[str]: return sorted({item.get("affected_asset", "") for item in self.store.findings() if item.get("affected_asset")})

    def summary(self) -> dict[str, Any]:
        findings = self.store.findings(); assets = self.store.assets(); scans = self.store.scans();
        return {"findings": {"total": len(findings), "open": sum(item.get("status") not in {"closed", "verified"} for item in findings), "high_or_critical": sum(item.get("severity") in {"high", "critical"} for item in findings)}, "assets": {"total": len(assets), "in_scope": sum(item.get("in_scope") is True for item in assets), "environments": self.environment_values()}, "scans": {"total": len(scans), "completed": sum(item.get("status") == "completed" for item in scans), "failed": sum(item.get("status") == "failed" for item in scans)}}

    def search_everything(self, query: str) -> dict[str, list[dict[str, Any]]]:
        text = self.normalize_query(query); return {"findings": self.find_findings(text).items, "assets": self.find_assets(text).items, "events": self.find_events(text).items}
