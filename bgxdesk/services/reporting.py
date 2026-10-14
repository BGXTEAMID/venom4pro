"""Deterministic reporting for offline SQLite projects."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import csv
import io
import json

from bgxdesk.services.sqlite_store import SQLiteStore, now


WEIGHTS = {"info": 0, "low": 1, "medium": 3, "high": 7, "critical": 12}


class ReportBuilder:
    def __init__(self, store: SQLiteStore) -> None: self.store = store

    def risk_score(self, findings: Iterable[dict[str, Any]] | None = None) -> int:
        rows = list(findings or self.store.findings()); return sum(WEIGHTS.get(row.get("severity", "info"), 0) for row in rows if row.get("status") not in {"closed", "verified"})

    def metrics(self) -> dict[str, Any]:
        status = self.store.status(); findings = self.store.findings(); status["open_risk_score"] = self.risk_score(findings); status["open_findings"] = sum(row.get("status") not in {"closed", "verified"} for row in findings); status["verified_findings"] = sum(row.get("status") == "verified" for row in findings); return status

    def markdown(self) -> str:
        status = self.metrics(); auth = self.store.authorization(); lines = ["# Venom4pro SQLite Assessment Report", "", f"Generated: {now()}", "", "## Project metrics", "", f"- Database: `{status['database']}`", f"- Open risk score: **{status['open_risk_score']}**", f"- Open findings: {status['open_findings']}", f"- Assets: {status['counts']['assets']}", f"- Scans: {status['counts']['scans']}", "", "## Active authorization", ""]
        if auth: lines.extend([f"- Client: **{auth['client']}**", f"- Engagement: **{auth['engagement']}**", f"- Reviewer: **{auth['reviewer']}**", f"- Window: `{auth['start_at']}` → `{auth['end_at']}`", "", "### Scope rules", ""] + [f"- {'IN' if rule['included'] else 'OUT'} `{rule['value']}` ({rule['kind']})" for rule in auth["rules"]])
        else: lines.append("No active authorization record.")
        lines.extend(["", "## Severity distribution", "", "| Severity | Count |", "|---|---:|"] + [f"| {key.upper()} | {value} |" for key, value in status["finding_by_severity"].items()])
        lines.extend(["", "## Findings", ""])
        for finding in self.store.findings(): lines.extend([f"### {finding['title']}", "", f"- Severity: **{finding['severity'].upper()}**", f"- Status: `{finding['status']}`", f"- Asset: `{finding['affected_asset']}`", f"- CVSS: `{finding['cvss'] if finding['cvss'] is not None else 'not scored'}`", "", finding["summary"], "", f"**Impact:** {finding['impact'] or 'Not documented.'}", "", f"**Remediation:** {finding['remediation'] or 'Not documented.'}", ""])
        lines.extend(["## Recent scans", "", "| Target | Status | Created |", "|---|---|---|"] + [f"| `{scan['target']}` | {scan['status']} | {scan['created_at']} |" for scan in self.store.scans()])
        return "\n".join(lines) + "\n"

    def csv(self) -> str:
        output = io.StringIO(); writer = csv.writer(output); writer.writerow(["id", "title", "severity", "status", "affected_asset", "cvss", "created_at"])
        for finding in self.store.findings(): writer.writerow([finding["id"], finding["title"], finding["severity"], finding["status"], finding["affected_asset"], finding["cvss"] or "", finding["created_at"]])
        return output.getvalue()

    def json(self) -> str:
        payload = {"generated_at": now(), "metrics": self.metrics(), "authorization": self.store.authorization(), "assets": self.store.assets(), "findings": self.store.findings(), "scans": self.store.scans(), "audit": self.store.audit_events(1000)}
        return json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    def write(self, path: str | Path, format_name: str | None = None) -> Path:
        destination = Path(path).expanduser().resolve(); destination.parent.mkdir(parents=True, exist_ok=True); format_name = format_name or destination.suffix.lstrip(".").lower() or "md"
        content = {"md": self.markdown, "markdown": self.markdown, "csv": self.csv, "json": self.json}.get(format_name)
        if content is None: raise ValueError(f"unsupported report format: {format_name}")
        destination.write_text(content(), encoding="utf-8"); self.store.audit("report_exported", "report", details={"path": str(destination), "format": format_name}); return destination
