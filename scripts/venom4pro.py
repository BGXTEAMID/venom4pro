#!/usr/bin/env python3
"""Venom4pro Kali Linux script mode.

Use this command line interface for local project management and authorized
read-only HTTP checks. It never performs credential guessing, exploit delivery,
state-changing HTTP methods, payload generation, or remote shell execution.
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import ssl
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bgxdesk.services.sqlite_store import SQLiteStore


SEVERITIES = {"info", "low", "medium", "high", "critical"}
WEIGHTS = {"info": 0, "low": 1, "medium": 3, "high": 7, "critical": 12}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def active_scope(store: SQLiteStore) -> dict | None:
    return store.authorization()


def target_in_scope(record: dict | None, target: str) -> bool:
    if not record or not record.get("active"): return False
    parsed = urlparse(target); host = (parsed.hostname or "").lower(); candidate = target.lower().rstrip("/")
    included = False
    for rule in record.get("rules", []):
        value = str(rule["value"]).strip().lower().rstrip("/")
        if value.startswith(("http://", "https://")): matched = candidate.startswith(value)
        elif value.startswith("*."): matched = host.endswith(value[1:])
        else: matched = value in {host, parsed.netloc.lower()} or host.endswith("." + value)
        if matched and not rule.get("included", True): return False
        if matched: included = True
    return included


def normalize_target(value: str) -> str:
    value = value.strip()
    if not value.startswith(("http://", "https://")): value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc: raise ValueError("target must be a valid http(s) URL")
    if parsed.username or parsed.password: raise ValueError("credentials in target are not accepted")
    return value.rstrip("/")


def request(url: str, timeout: float, delay_state: dict, delay: float, verify_tls: bool = True, method: str = "GET", max_body: int = 512000) -> tuple[int, dict[str, str], bytes, str]:
    import time
    elapsed = time.monotonic() - delay_state.get("last", 0.0)
    if elapsed < delay: time.sleep(delay - elapsed)
    delay_state["last"] = time.monotonic()
    if method not in {"GET", "HEAD"}: raise ValueError("only GET and HEAD are allowed")
    req = Request(url, method=method, headers={"User-Agent": "Venom4pro/3.0 Kali authorized-read-only", "Accept": "text/html,application/json,application/xml,text/plain,*/*;q=0.5"})
    context = ssl.create_default_context() if verify_tls else ssl._create_unverified_context()
    try:
        with urlopen(req, timeout=timeout, context=context) as response: return response.status, {k.lower(): v for k, v in response.headers.items()}, response.read(max_body), response.geturl()
    except HTTPError as exc: return exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read(max_body), exc.geturl()


def scan(store: SQLiteStore, args: argparse.Namespace) -> dict:
    target = normalize_target(args.target)
    if not target_in_scope(active_scope(store), target): raise PermissionError("target is outside active authorization scope")
    events: list[dict] = []; delay = {"last": 0.0}
    def add(check: str, status: str, severity: str = "info", summary: str = "", details: dict | None = None, url: str = target) -> None: events.append({"check": check, "status": status, "severity": severity, "summary": summary, "details": details or {}, "url": url, "created_at": utc_now()})
    try:
        status, headers, body, final = request(target, args.timeout, delay, args.delay, args.verify_tls, max_body=args.max_body)
        add("http-response", "ok", "medium" if status >= 500 else "info", f"HTTP {status}", {"status": status, "final_url": final, "content_type": headers.get("content-type", ""), "body_bytes": len(body)})
        if target.startswith("https://") and final.startswith("http://"): add("redirect", "finding", "low", "HTTPS ended on HTTP URL", {"final_url": final})
        required = {"strict-transport-security": "medium", "content-security-policy": "low", "x-content-type-options": "low", "referrer-policy": "info", "permissions-policy": "info"}
        missing = [name for name in required if name not in headers]; add("security-headers", "ok", "info", f"{len(missing)} recommended headers absent", {"missing": missing})
        for name in missing: add("header:" + name, "finding", required[name], "Recommended security header absent")
        cookie = headers.get("set-cookie", "").lower()
        for flag in ("secure", "httponly", "samesite"):
            if cookie and flag not in cookie: add("cookie:" + flag, "finding", "low", f"Cookie may omit {flag} attribute")
        sample = (body[:100000].decode("utf-8", errors="ignore") + " " + headers.get("server", "") + " " + headers.get("x-powered-by", "")).lower()
        signatures = {"wordpress": "wordpress", "django": "csrfmiddlewaretoken", "laravel": "laravel", "react": "react", "vue": "vue", "nginx": "nginx", "apache": "apache", "php": ".php"}
        add("technology", "ok", "info", "Passive technology hints", {"detected": sorted(k for k, v in signatures.items() if v in sample)})
        if headers.get("server") or headers.get("x-powered-by"): add("technology-disclosure", "finding", "low", "Response discloses technology headers", {"server": headers.get("server", ""), "x-powered-by": headers.get("x-powered-by", "")})
        parsed = urlparse(target)
        if parsed.scheme != "https": add("tls", "finding", "medium", "Target is not using HTTPS")
        else:
            try:
                context = ssl.create_default_context()
                with socket.create_connection((parsed.hostname, parsed.port or 443), timeout=args.timeout) as sock:
                    with context.wrap_socket(sock, server_hostname=parsed.hostname) as tls_sock: add("tls", "ok", "info", "TLS handshake succeeded", {"version": tls_sock.version(), "cipher": tls_sock.cipher()[0] if tls_sock.cipher() else ""})
            except (OSError, ssl.SSLError) as exc: add("tls", "error", "medium", "TLS handshake failed", {"error": str(exc)})
        optional = [("/robots.txt", args.robots, "robots"), ("/sitemap.xml", args.sitemap, "sitemap"), ("/openapi.json", args.openapi, "openapi"), ("/swagger.json", args.openapi, "openapi")]
        for path, enabled, label in optional:
            if not enabled: continue
            resource = urljoin(target + "/", path.lstrip("/"))
            try:
                code, resource_headers, resource_body, final_resource = request(resource, args.timeout, delay, args.delay, args.verify_tls, max_body=args.max_body)
                add(label + path, "found" if code < 400 else "absent", "info", f"Optional resource returned HTTP {code}", {"content_type": resource_headers.get("content-type", ""), "body_bytes": len(resource_body)}, final_resource)
            except (OSError, URLError, TimeoutError) as exc: add(label + path, "error", "info", "Optional resource unavailable", {"error": str(exc)}, resource)
    except (OSError, URLError, TimeoutError, ValueError) as exc: result = {"status": "failed", "error": str(exc), "events": events}; store.add_scan(target, result, str(exc)); return result
    summary = {severity: sum(event["severity"] == severity for event in events) for severity in SEVERITIES}; summary["events"] = len(events); result = {"status": "completed", "target": target, "summary": summary, "events": events}; store.add_scan(target, result); return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="venom4pro", description="Venom4pro authorized Kali Linux script mode")
    parser.add_argument("--db", default=None, help="SQLite path; default ~/.local/share/venom4pro/venom4pro.db")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="initialize SQLite database")
    sub.add_parser("status", help="show database counts")
    auth = sub.add_parser("authorization", help="create authorization from JSON")
    auth.add_argument("json_file")
    asset = sub.add_parser("asset", help="add asset from JSON")
    asset.add_argument("json_file")
    finding = sub.add_parser("finding", help="add finding from JSON")
    finding.add_argument("json_file")
    transition = sub.add_parser("transition", help="move finding status")
    transition.add_argument("finding_id"); transition.add_argument("status")
    scan_parser = sub.add_parser("scan", help="authorized read-only HTTP assessment")
    scan_parser.add_argument("target"); scan_parser.add_argument("--timeout", type=float, default=8); scan_parser.add_argument("--delay", type=float, default=0.6); scan_parser.add_argument("--max-body", type=int, default=512000); scan_parser.add_argument("--no-robots", dest="robots", action="store_false"); scan_parser.add_argument("--no-sitemap", dest="sitemap", action="store_false"); scan_parser.add_argument("--no-openapi", dest="openapi", action="store_false"); scan_parser.add_argument("--no-verify-tls", dest="verify_tls", action="store_false")
    report = sub.add_parser("report", help="export a Markdown report")
    report.add_argument("output")
    sub.add_parser("audit", help="show recent audit events")
    return parser


def main() -> int:
    args = build_parser().parse_args(); store = SQLiteStore(args.db)
    try:
        if args.command == "init": emit({"status": "initialized", "database": str(store.path)})
        elif args.command == "status": emit(store.status())
        elif args.command == "authorization": emit(store.add_authorization(json.loads(Path(args.json_file).read_text(encoding="utf-8"))))
        elif args.command == "asset":
            data = json.loads(Path(args.json_file).read_text(encoding="utf-8")); scope = active_scope(store); in_scope = target_in_scope(scope, data["name"] if data["name"].startswith("http") else "https://" + data["name"]); emit(store.add_asset(data, in_scope))
        elif args.command == "finding": emit(store.add_finding(json.loads(Path(args.json_file).read_text(encoding="utf-8"))))
        elif args.command == "transition": emit(store.transition_finding(args.finding_id, args.status))
        elif args.command == "scan": emit(scan(store, args))
        elif args.command == "audit": emit(store.audit_events())
        elif args.command == "report":
            status = store.status(); findings = store.findings(); lines = ["# Venom4pro SQLite Assessment Report", "", f"Generated: {utc_now()}", "", f"- Database: `{status['database']}`", f"- Risk score: {sum(WEIGHTS.get(item['severity'], 0) for item in findings if item['status'] not in {'closed','verified'})}", "", "## Findings", ""]
            for item in findings: lines.extend([f"### {item['title']}", "", f"- Severity: **{item['severity'].upper()}**", f"- Status: `{item['status']}`", f"- Asset: `{item['affected_asset']}`", "", item["summary"], "", f"Remediation: {item['remediation'] or 'Not documented.'}", ""])
            Path(args.output).expanduser().write_text("\n".join(lines), encoding="utf-8"); emit({"status": "exported", "path": str(Path(args.output).expanduser().resolve())})
        return 0
    except (ValueError, KeyError, PermissionError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2


if __name__ == "__main__": raise SystemExit(main())
