"""Authorized, read-only web assessment engine.

This module deliberately avoids credential guessing, payload delivery, exploit
execution, file upload, or state-changing HTTP methods. It performs metadata
and configuration checks against explicitly authorized URLs.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from time import monotonic, sleep
from typing import Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, build_opener, urlopen
import json
import re
import socket
import ssl

from bgxdesk.domain.models import AuditEvent, Evidence, Severity, utc_now
from bgxdesk.services.assessment import AuthorizationService
from bgxdesk.services.storage import Repository


SAFE_METHODS = {"GET", "HEAD"}
DEFAULT_USER_AGENT = "BGXTEAM-Security-Desk/2.0 authorized-read-only"


@dataclass(frozen=True)
class ScanConfig:
    timeout_seconds: float = 8.0
    delay_seconds: float = 0.6
    max_redirects: int = 5
    max_body_bytes: int = 512_000
    include_robots: bool = True
    include_sitemap: bool = True
    include_openapi: bool = True
    verify_tls: bool = True
    user_agent: str = DEFAULT_USER_AGENT

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not 0.5 <= self.timeout_seconds <= 60:
            errors.append("timeout_seconds must be between 0.5 and 60")
        if not 0 <= self.delay_seconds <= 30:
            errors.append("delay_seconds must be between 0 and 30")
        if not 0 <= self.max_redirects <= 20:
            errors.append("max_redirects must be between 0 and 20")
        if not 1_024 <= self.max_body_bytes <= 10_000_000:
            errors.append("max_body_bytes must be between 1024 and 10000000")
        return errors


@dataclass
class ScanEvent:
    check: str
    url: str
    status: str
    severity: Severity = Severity.INFO
    summary: str = ""
    details: dict[str, object] | None = None
    started_at: str = ""
    finished_at: str = ""

    def __post_init__(self) -> None:
        self.details = self.details or {}
        if not self.started_at:
            self.started_at = utc_now()
        if not self.finished_at:
            self.finished_at = utc_now()

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["severity"] = self.severity.value
        return data


@dataclass
class ScanResult:
    target: str
    started_at: str
    finished_at: str = ""
    status: str = "running"
    events: list[ScanEvent] | None = None
    error: str = ""

    def __post_init__(self) -> None:
        if self.events is None:
            self.events = []

    def add(self, event: ScanEvent) -> None:
        self.events.append(event)

    def summary(self) -> dict[str, int | str]:
        counts = {severity.value: 0 for severity in Severity}
        for event in self.events:
            counts[event.severity.value] += 1
        counts.update({"target": self.target, "status": self.status, "events": len(self.events)})
        return counts

    def to_json(self) -> str:
        return json.dumps({"target": self.target, "started_at": self.started_at, "finished_at": self.finished_at, "status": self.status, "error": self.error, "summary": self.summary(), "events": [event.as_dict() for event in self.events]}, indent=2, ensure_ascii=False)


class ScopeViolation(PermissionError):
    pass


class ScanCancelled(RuntimeError):
    pass


class ReadOnlyScanner:
    def __init__(self, repository: Repository, config: ScanConfig | None = None) -> None:
        self.repository = repository
        self.config = config or ScanConfig()
        errors = self.config.validate()
        if errors:
            raise ValueError("; ".join(errors))
        self.authorization = AuthorizationService(repository)
        self.stop_event = Event()
        self.progress_callback: Callable[[ScanEvent], None] | None = None
        self._last_request_at = 0.0

    def stop(self) -> None:
        self.stop_event.set()

    def reset(self) -> None:
        self.stop_event.clear()

    def _check_cancelled(self) -> None:
        if self.stop_event.is_set():
            raise ScanCancelled("Scan stopped by operator")

    def _wait_rate_limit(self) -> None:
        elapsed = monotonic() - self._last_request_at
        if elapsed < self.config.delay_seconds:
            sleep(self.config.delay_seconds - elapsed)
        self._last_request_at = monotonic()

    def normalize_target(self, target: str) -> str:
        value = target.strip()
        if not value:
            raise ValueError("Target is empty")
        if not re.match(r"^https?://", value, re.I):
            value = "https://" + value
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Only valid http:// or https:// targets are accepted")
        if parsed.username or parsed.password:
            raise ValueError("Credentials in target URLs are not accepted")
        return value.rstrip("/")

    def enforce_scope(self, target: str) -> str:
        normalized = self.normalize_target(target)
        allowed, reason = self.authorization.check_target(normalized)
        if not allowed:
            raise ScopeViolation(reason)
        return normalized

    def request(self, url: str, method: str = "GET") -> tuple[int, dict[str, str], bytes, str]:
        self._check_cancelled()
        if method not in SAFE_METHODS:
            raise ValueError(f"Method {method} is not allowed")
        self._wait_rate_limit()
        request = Request(url, method=method, headers={"User-Agent": self.config.user_agent, "Accept": "text/html,application/json,application/xml,text/plain,*/*;q=0.5"})
        context = None if self.config.verify_tls else ssl._create_unverified_context()
        try:
            with urlopen(request, timeout=self.config.timeout_seconds, context=context) as response:
                headers = {key.lower(): value for key, value in response.headers.items()}
                body = response.read(self.config.max_body_bytes)
                return response.status, headers, body, response.geturl()
        except HTTPError as exc:
            headers = {key.lower(): value for key, value in exc.headers.items()}
            return exc.code, headers, exc.read(self.config.max_body_bytes), exc.geturl()

    def emit(self, result: ScanResult, event: ScanEvent) -> None:
        result.add(event)
        if self.progress_callback:
            self.progress_callback(event)

    def run(self, target: str) -> ScanResult:
        normalized = self.enforce_scope(target)
        self.reset()
        result = ScanResult(normalized, utc_now())
        self.repository.append_event(AuditEvent("scan_started", "scan", details={"target": normalized, "mode": "read-only"}))
        try:
            self.check_http(result, normalized)
            self.check_security_headers(result, normalized)
            self.check_cookies(result, normalized)
            self.check_technology(result, normalized)
            self.check_tls(result, normalized)
            if self.config.include_robots:
                self.check_auxiliary(result, normalized, "/robots.txt", "robots")
            if self.config.include_sitemap:
                self.check_auxiliary(result, normalized, "/sitemap.xml", "sitemap")
            if self.config.include_openapi:
                for path in ("/openapi.json", "/swagger.json", "/api-docs"):
                    self.check_auxiliary(result, normalized, path, "openapi")
                    if self.stop_event.is_set(): break
            result.status = "cancelled" if self.stop_event.is_set() else "completed"
        except ScanCancelled as exc:
            result.status = "cancelled"; result.error = str(exc)
        except (OSError, ValueError, ScopeViolation) as exc:
            result.status = "failed"; result.error = str(exc)
            self.emit(result, ScanEvent("scan", normalized, "error", Severity.MEDIUM, str(exc)))
        finally:
            result.finished_at = utc_now()
            self.persist_result(result)
        return result

    def persist_result(self, result: ScanResult) -> None:
        payload = result.to_json()
        evidence = Evidence(f"Automatic read-only scan: {result.target}", payload, "read-only-scanner")
        self.repository.snapshot.evidence.append(evidence)
        self.repository.append_event(AuditEvent("scan_finished", "scan", details={"target": result.target, "status": result.status, "summary": result.summary(), "evidence_id": evidence.id}))

    def check_http(self, result: ScanResult, url: str) -> None:
        started = utc_now()
        try:
            status, headers, body, final_url = self.request(url)
            severity = Severity.INFO if status < 500 else Severity.MEDIUM
            self.emit(result, ScanEvent("http-response", url, "ok", severity, f"HTTP {status}", {"status": status, "final_url": final_url, "content_type": headers.get("content-type", ""), "body_bytes": len(body)}, started, utc_now()))
            if final_url.startswith("http://") and url.startswith("https://"):
                self.emit(result, ScanEvent("redirect", url, "finding", Severity.LOW, "HTTPS request ended on HTTP URL", {"final_url": final_url}))
        except (HTTPError, URLError, TimeoutError, socket.timeout) as exc:
            self.emit(result, ScanEvent("http-response", url, "error", Severity.MEDIUM, "HTTP request failed", {"error": str(exc)}, started, utc_now()))

    def check_security_headers(self, result: ScanResult, url: str) -> None:
        try:
            status, headers, _, _ = self.request(url, "HEAD")
        except (HTTPError, URLError, TimeoutError, socket.timeout) as exc:
            self.emit(result, ScanEvent("security-headers", url, "error", Severity.INFO, "Header check unavailable", {"error": str(exc)})); return
        required = {"strict-transport-security": Severity.MEDIUM, "content-security-policy": Severity.LOW, "x-content-type-options": Severity.LOW, "referrer-policy": Severity.INFO, "permissions-policy": Severity.INFO}
        missing = [key for key in required if key not in headers]
        self.emit(result, ScanEvent("security-headers", url, "ok", Severity.INFO, f"HTTP {status}; {len(missing)} recommended headers absent", {"present": sorted(set(required) - set(missing)), "missing": missing}))
        for header in missing:
            self.emit(result, ScanEvent(f"header:{header}", url, "finding", required[header], f"Recommended header is absent: {header}"))

    def check_cookies(self, result: ScanResult, url: str) -> None:
        try:
            _, headers, _, _ = self.request(url)
        except (HTTPError, URLError, TimeoutError, socket.timeout): return
        raw = headers.get("set-cookie", "")
        if not raw: return
        lower = raw.lower()
        for flag, severity in (("secure", Severity.LOW), ("httponly", Severity.LOW), ("samesite", Severity.LOW)):
            if flag not in lower:
                self.emit(result, ScanEvent(f"cookie:{flag}", url, "finding", severity, f"Cookie response may omit {flag} attribute", {"set_cookie_present": True}))

    def check_technology(self, result: ScanResult, url: str) -> None:
        try:
            _, headers, body, _ = self.request(url)
        except (HTTPError, URLError, TimeoutError, socket.timeout): return
        sample = (body[:100_000].decode("utf-8", errors="ignore") + " " + headers.get("server", "") + " " + headers.get("x-powered-by", "")).lower()
        signatures = {"wordpress": "wordpress", "django": "csrfmiddlewaretoken", "laravel": "laravel", "react": "react", "vue": "vue", "nginx": "nginx", "apache": "apache", "php": ".php"}
        detected = sorted(name for name, signature in signatures.items() if signature in sample)
        self.emit(result, ScanEvent("technology", url, "ok", Severity.INFO, "Technology hints collected from response", {"detected": detected, "server_header_present": "server" in headers, "powered_by_present": "x-powered-by" in headers}))
        if "server" in headers or "x-powered-by" in headers:
            self.emit(result, ScanEvent("technology-disclosure", url, "finding", Severity.LOW, "Response discloses server technology headers", {"server": headers.get("server", ""), "x-powered-by": headers.get("x-powered-by", "")}))

    def check_tls(self, result: ScanResult, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            self.emit(result, ScanEvent("tls", url, "finding", Severity.MEDIUM, "Target is not using HTTPS")); return
        try:
            context = ssl.create_default_context()
            with socket.create_connection((parsed.hostname, parsed.port or 443), timeout=self.config.timeout_seconds) as sock:
                with context.wrap_socket(sock, server_hostname=parsed.hostname) as secured:
                    certificate = secured.getpeercert()
                    self.emit(result, ScanEvent("tls", url, "ok", Severity.INFO, "TLS handshake succeeded", {"version": secured.version(), "cipher": secured.cipher()[0] if secured.cipher() else "", "subject": str(certificate.get("subject", ""))}))
        except (OSError, ssl.SSLError) as exc:
            self.emit(result, ScanEvent("tls", url, "error", Severity.MEDIUM, "TLS handshake failed", {"error": str(exc)}))

    def check_auxiliary(self, result: ScanResult, base: str, path: str, check_name: str) -> None:
        try:
            status, headers, body, final_url = self.request(urljoin(base + "/", path.lstrip("/")))
            if status < 400:
                self.emit(result, ScanEvent(f"{check_name}:{path}", final_url, "found", Severity.INFO, f"Optional resource returned HTTP {status}", {"content_type": headers.get("content-type", ""), "body_bytes": len(body)}))
            else:
                self.emit(result, ScanEvent(f"{check_name}:{path}", final_url, "absent", Severity.INFO, f"Optional resource returned HTTP {status}"))
        except (HTTPError, URLError, TimeoutError, socket.timeout) as exc:
            self.emit(result, ScanEvent(f"{check_name}:{path}", base, "error", Severity.INFO, "Optional resource unavailable", {"error": str(exc)}))


def scan_to_markdown(result: ScanResult) -> str:
    lines = [f"# Automatic Read-Only Scan", "", f"- Target: `{result.target}`", f"- Status: **{result.status}**", f"- Started: {result.started_at}", f"- Finished: {result.finished_at}", "", "## Summary", ""]
    lines.extend(f"- {key}: {value}" for key, value in result.summary().items())
    lines.extend(["", "## Events", "", "| Check | Severity | Status | Summary |", "|---|---|---|---|"])
    lines.extend(f"| {event.check} | {event.severity.value} | {event.status} | {event.summary.replace('|', '/') } |" for event in result.events)
    return "\n".join(lines) + "\n"
