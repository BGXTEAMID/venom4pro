"""Deterministic analytics for findings, scans, and audit records."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable
import math
import re


WEIGHTS = {"info": 0, "low": 1, "medium": 3, "high": 7, "critical": 12}
STATUS_OPEN = {"draft", "open", "accepted", "remediated"}


@dataclass(frozen=True)
class FindingFingerprint:
    title: str
    asset: str
    category: str

    def key(self) -> str: return "|".join(value.strip().lower() for value in (self.title, self.asset, self.category))


class FindingAnalytics:
    def __init__(self, findings: Iterable[dict[str, Any]]) -> None: self.findings = list(findings)

    def counts_by(self, field: str) -> dict[str, int]: return dict(Counter(str(item.get(field, "unknown")) for item in self.findings))

    def severity_counts(self) -> dict[str, int]: return {name: self.counts_by("severity").get(name, 0) for name in WEIGHTS}

    def status_counts(self) -> dict[str, int]: return self.counts_by("status")

    def risk_score(self) -> int: return sum(WEIGHTS.get(item.get("severity", "info"), 0) for item in self.findings if item.get("status") in STATUS_OPEN)

    def weighted_average(self) -> float: 
        open_items = [item for item in self.findings if item.get("status") in STATUS_OPEN]
        return round(sum(WEIGHTS.get(item.get("severity", "info"), 0) for item in open_items) / len(open_items), 2) if open_items else 0.0

    def critical_path(self) -> list[dict[str, Any]]: return sorted((item for item in self.findings if item.get("status") in STATUS_OPEN), key=lambda item: (-WEIGHTS.get(item.get("severity", "info"), 0), -(float(item.get("cvss") or 0)), item.get("created_at", "")))

    def by_asset(self) -> dict[str, dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for item in self.findings:
            asset = item.get("affected_asset", "unknown"); bucket = grouped.setdefault(asset, {"asset": asset, "count": 0, "risk_score": 0, "severities": {name: 0 for name in WEIGHTS}}); bucket["count"] += 1; severity = item.get("severity", "info"); bucket["severities"][severity] = bucket["severities"].get(severity, 0) + 1; bucket["risk_score"] += WEIGHTS.get(severity, 0) if item.get("status") in STATUS_OPEN else 0
        return grouped

    def duplicate_groups(self) -> list[list[dict[str, Any]]]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in self.findings:
            fingerprint = FindingFingerprint(item.get("title", ""), item.get("affected_asset", ""), self.category(item.get("title", ""))).key(); groups[fingerprint].append(item)
        return [items for items in groups.values() if len(items) > 1]

    @staticmethod
    def category(title: str) -> str:
        text = title.lower()
        for label, tokens in {"authentication": ("auth", "login", "session"), "authorization": ("access", "idor", "permission"), "configuration": ("header", "tls", "cookie", "config"), "injection": ("injection", "sql", "xss"), "information": ("disclosure", "leak", "exposure")}.items():
            if any(token in text for token in tokens): return label
        return "other"

    def remediation_queue(self) -> list[dict[str, Any]]:
        queue = []
        for item in self.critical_path():
            queue.append({"id": item.get("id"), "title": item.get("title"), "asset": item.get("affected_asset"), "severity": item.get("severity"), "priority": WEIGHTS.get(item.get("severity", "info"), 0), "has_remediation": bool(str(item.get("remediation", "")).strip()), "has_impact": bool(str(item.get("impact", "")).strip())})
        return queue

    def report(self) -> dict[str, Any]: return {"total": len(self.findings), "severity": self.severity_counts(), "status": self.status_counts(), "risk_score": self.risk_score(), "weighted_average": self.weighted_average(), "by_asset": self.by_asset(), "duplicate_groups": self.duplicate_groups(), "remediation_queue": self.remediation_queue()}


class ScanAnalytics:
    def __init__(self, scans: Iterable[dict[str, Any]]) -> None: self.scans = list(scans)

    def status_counts(self) -> dict[str, int]: return dict(Counter(str(item.get("status", "unknown")) for item in self.scans))

    def event_counts(self) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for scan in self.scans:
            for event in scan.get("result", {}).get("events", []): counter[event.get("check", "unknown")] += 1
        return dict(counter)

    def finding_event_counts(self) -> dict[str, int]:
        counter: Counter[str] = Counter()
        for scan in self.scans:
            for event in scan.get("result", {}).get("events", []):
                if event.get("status") == "finding": counter[event.get("severity", "info")] += 1
        return dict(counter)

    def targets(self) -> list[str]: return sorted({str(item.get("target", "")) for item in self.scans})

    def report(self) -> dict[str, Any]: return {"total_scans": len(self.scans), "statuses": self.status_counts(), "targets": self.targets(), "event_counts": self.event_counts(), "finding_events": self.finding_event_counts()}


class AuditAnalytics:
    def __init__(self, events: Iterable[dict[str, Any]]) -> None: self.events = list(events)

    def actions(self) -> dict[str, int]: return dict(Counter(str(item.get("action", "unknown")) for item in self.events))

    def entities(self) -> dict[str, int]: return dict(Counter(str(item.get("entity", "unknown")) for item in self.events))

    def timeline(self) -> list[dict[str, Any]]: return sorted(self.events, key=lambda item: item.get("created_at", ""))

    def report(self) -> dict[str, Any]: return {"total": len(self.events), "actions": self.actions(), "entities": self.entities(), "first": self.timeline()[0] if self.events else None, "last": self.timeline()[-1] if self.events else None}


def parse_iso(value: str) -> datetime | None:
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError): return None


def redact_text(text: str, patterns: Iterable[str] = (r"(?i)bearer\s+[A-Za-z0-9._-]+", r"(?i)(password|secret|token)=([^\s&]+)")) -> str:
    result = text
    for pattern in patterns: result = re.sub(pattern, "[REDACTED]", result)
    return result
