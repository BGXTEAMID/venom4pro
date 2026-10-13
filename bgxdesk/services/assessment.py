"""Assessment services: local inventory, scope checks, metrics, and reporting."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
import csv
import json
import shutil
import subprocess

from bgxdesk.domain.models import (
    Asset, AuditEvent, AuthorizationRecord, Evidence, Finding, FindingStatus,
    Policy, ProjectSnapshot, Severity, ToolRecord, utc_now,
)
from bgxdesk.services.storage import Repository


DEFAULT_TOOLS: tuple[ToolRecord, ...] = (
    ToolRecord("nmap", "Network Discovery", "Host and service inventory", "nmap", Policy.SAFE, documentation_url="https://nmap.org/docs.html"),
    ToolRecord("httpx", "Web Assessment", "HTTP metadata inspection", "httpx", Policy.REVIEW),
    ToolRecord("nuclei", "Web Assessment", "Template-based checks", "nuclei", Policy.REVIEW),
    ToolRecord("ffuf", "Content Discovery", "Content discovery utility", "ffuf", Policy.RESTRICTED),
    ToolRecord("burpsuite", "Web Assessment", "Intercepting proxy", "burpsuite", Policy.REVIEW),
    ToolRecord("zaproxy", "Web Assessment", "Web security proxy", "zaproxy", Policy.REVIEW),
    ToolRecord("wireshark", "Traffic Analysis", "Packet analysis GUI", "wireshark", Policy.SAFE),
    ToolRecord("tcpdump", "Traffic Analysis", "Packet capture inspection", "tcpdump", Policy.SAFE),
    ToolRecord("semgrep", "Code Security", "Static analysis rules", "semgrep", Policy.SAFE),
    ToolRecord("bandit", "Code Security", "Python security linting", "bandit", Policy.SAFE),
    ToolRecord("pip-audit", "Dependency Security", "Python dependency audit", "pip-audit", Policy.SAFE),
    ToolRecord("trivy", "Container Security", "Filesystem and image scanner", "trivy", Policy.REVIEW),
    ToolRecord("jadx", "Mobile Analysis", "Android decompiler", "jadx", Policy.SAFE),
    ToolRecord("apktool", "Mobile Analysis", "Android package inspection", "apktool", Policy.SAFE),
    ToolRecord("adb", "Mobile Analysis", "Android debugging bridge", "adb", Policy.REVIEW),
    ToolRecord("ghidra", "Reverse Engineering", "Binary analysis suite", "ghidra", Policy.SAFE),
    ToolRecord("radare2", "Reverse Engineering", "Reverse engineering toolkit", "r2", Policy.SAFE),
    ToolRecord("gdb", "Debugging", "GNU debugger", "gdb", Policy.SAFE),
    ToolRecord("git", "Project Utilities", "Version control", "git", Policy.SAFE),
    ToolRecord("docker", "Project Utilities", "Container runtime", "docker", Policy.REVIEW),
)


@dataclass(frozen=True)
class ToolCheckResult:
    name: str
    installed: bool
    executable: str
    resolved_path: str = ""
    version: str = ""
    error: str = ""
    checked_at: str = ""


class InventoryService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository
        self.ensure_defaults()

    def ensure_defaults(self) -> None:
        existing = {tool.name for tool in self.repository.snapshot.tools}
        missing = [ToolRecord(**tool.__dict__) for tool in DEFAULT_TOOLS if tool.name not in existing]
        if missing:
            self.repository.snapshot.tools.extend(missing)
            self.repository.save()

    def check(self, tool: ToolRecord, timeout: float = 4.0) -> ToolCheckResult:
        checked_at = utc_now()
        path = shutil.which(tool.executable)
        if not path:
            for alias in tool.aliases:
                path = shutil.which(alias)
                if path:
                    break
        if not path:
            return ToolCheckResult(tool.name, False, tool.executable, checked_at=checked_at)
        version = ""
        error = ""
        try:
            result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=timeout, check=False)
            version = (result.stdout or result.stderr).strip().splitlines()[0][:240] if (result.stdout or result.stderr).strip() else f"exit {result.returncode}"
        except (OSError, subprocess.TimeoutExpired) as exc:
            error = str(exc)
        return ToolCheckResult(tool.name, True, tool.executable, path, version, error, checked_at)

    def check_all(self) -> list[ToolCheckResult]:
        results = [self.check(tool) for tool in self.repository.snapshot.tools]
        by_name = {item.name: item for item in results}
        for tool in self.repository.snapshot.tools:
            result = by_name[tool.name]
            tool.installed = result.installed
            tool.version = result.version
            tool.last_checked = result.checked_at
        self.repository.save()
        self.repository.append_event(AuditEvent("inventory_refresh", "tools", details={"checked": len(results), "installed": sum(item.installed for item in results)}))
        return results

    def categories(self) -> list[str]:
        return sorted({tool.category for tool in self.repository.snapshot.tools})

    def filter(self, query: str = "", category: str = "All categories", policy: str = "All policies") -> list[ToolRecord]:
        text = query.strip().lower()
        return [tool for tool in self.repository.snapshot.tools if (not text or text in " ".join((tool.name, tool.category, tool.purpose, tool.executable)).lower()) and (category == "All categories" or tool.category == category) and (policy == "All policies" or tool.policy.value == policy)]


class AuthorizationService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def active(self) -> AuthorizationRecord | None:
        return next((item for item in reversed(self.repository.snapshot.authorizations) if item.active), None)

    def create(self, record: AuthorizationRecord) -> AuthorizationRecord:
        errors = record.validate()
        if errors:
            raise ValueError("; ".join(errors))
        self.repository.add("authorizations", record)
        self.repository.append_event(AuditEvent("authorization_created", "authorization", record.id, details={"client": record.client, "engagement": record.engagement}))
        return record

    def check_target(self, target: str) -> tuple[bool, str]:
        record = self.active()
        if not record:
            return False, "No active authorization record"
        if not record.is_in_scope(target):
            return False, "Target is outside the active scope"
        return True, "Target is in scope"

    def add_asset(self, asset: Asset) -> Asset:
        record = self.active()
        asset.in_scope = bool(record and record.is_in_scope(asset.name))
        errors = asset.validate()
        if errors:
            raise ValueError("; ".join(errors))
        self.repository.add("assets", asset)
        self.repository.append_event(AuditEvent("asset_created", "asset", asset.id, details={"name": asset.name, "in_scope": asset.in_scope}))
        return asset


class FindingsService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def create(self, finding: Finding) -> Finding:
        errors = finding.validate()
        if errors:
            raise ValueError("; ".join(errors))
        self.repository.add("findings", finding)
        self.repository.append_event(AuditEvent("finding_created", "finding", finding.id, details={"severity": finding.severity.value, "title": finding.title}))
        return finding

    def transition(self, finding_id: str, status: FindingStatus) -> Finding:
        finding = self.repository.get("findings", finding_id)
        if not finding:
            raise KeyError(finding_id)
        old = finding.status.value
        finding.transition(status)
        self.repository.save()
        self.repository.append_event(AuditEvent("finding_transitioned", "finding", finding.id, details={"from": old, "to": status.value}))
        return finding

    def attach_evidence(self, finding_id: str, evidence: Evidence) -> Finding:
        errors = evidence.validate()
        if errors:
            raise ValueError("; ".join(errors))
        finding = self.repository.get("findings", finding_id)
        if not finding:
            raise KeyError(finding_id)
        self.repository.snapshot.evidence.append(evidence)
        if evidence.id not in finding.evidence_ids:
            finding.evidence_ids.append(evidence.id)
        finding.updated_at = utc_now()
        self.repository.save()
        self.repository.append_event(AuditEvent("evidence_attached", "finding", finding.id, details={"evidence_id": evidence.id}))
        return finding

    def by_severity(self) -> dict[str, int]:
        return {severity.value: sum(item.severity == severity for item in self.repository.snapshot.findings) for severity in Severity}

    def risk_score(self) -> int:
        weights = {Severity.INFO: 0, Severity.LOW: 1, Severity.MEDIUM: 3, Severity.HIGH: 7, Severity.CRITICAL: 12}
        return sum(weights[item.severity] for item in self.repository.snapshot.findings if item.status not in {FindingStatus.CLOSED, FindingStatus.VERIFIED})


class ReportService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def markdown(self) -> str:
        snapshot = self.repository.snapshot
        counts = FindingsService(self.repository).by_severity()
        lines = ["# BGXTEAM Security Desk Report", "", f"Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}", "", "## Executive summary", "", f"- Assets: {len(snapshot.assets)}", f"- Findings: {len(snapshot.findings)}", f"- Evidence items: {len(snapshot.evidence)}", "", "## Severity summary", "", "| Severity | Count |", "|---|---:|"]
        lines.extend(f"| {key.upper()} | {value} |" for key, value in counts.items())
        lines.extend(["", "## Scope and authorization", "", self.authorization_markdown(), "", "## Findings", ""])
        lines.extend(item.as_markdown() for item in snapshot.findings)
        lines.extend(["", "## Audit trail", ""])
        lines.extend(f"- `{event.created_at}` **{event.action}** {event.entity} `{event.entity_id}`" for event in snapshot.events[-100:])
        return "\n".join(lines).strip() + "\n"

    def authorization_markdown(self) -> str:
        record = AuthorizationService(self.repository).active()
        if not record:
            return "No active authorization record is configured."
        scope = "\n".join(f"- {'IN' if rule.included else 'OUT'} `{rule.value}` ({rule.kind.value})" for rule in record.rules)
        return f"**Client:** {record.client}\n\n**Engagement:** {record.engagement}\n\n**Reviewer:** {record.reviewer}\n\n**Window:** {record.start_at} to {record.end_at}\n\n**Scope:**\n{scope}"

    def export_markdown(self, path: str | Path) -> Path:
        destination = Path(path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(self.markdown(), encoding="utf-8")
        self.repository.append_event(AuditEvent("report_exported", "report", details={"path": str(destination), "format": "markdown"}))
        return destination

    def export_csv(self, path: str | Path) -> Path:
        destination = Path(path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id", "title", "severity", "status", "asset", "cvss", "assignee", "created_at"])
            for item in self.repository.snapshot.findings:
                writer.writerow([item.id, item.title, item.severity.value, item.status.value, item.affected_asset, item.cvss if item.cvss is not None else "", item.assignee, item.created_at])
        self.repository.append_event(AuditEvent("report_exported", "report", details={"path": str(destination), "format": "csv"}))
        return destination

    def export_json(self, path: str | Path) -> Path:
        destination = Path(path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = {"generated_at": utc_now(), "snapshot": {"counts": self.repository.snapshot.counts(), "findings": [item.__dict__ for item in self.repository.snapshot.findings]}}
        destination.write_text(json.dumps(payload, indent=2, default=lambda value: value.value if hasattr(value, "value") else str(value)), encoding="utf-8")
        self.repository.append_event(AuditEvent("report_exported", "report", details={"path": str(destination), "format": "json"}))
        return destination
