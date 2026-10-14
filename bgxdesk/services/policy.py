"""Policy and validation services for local authorized assessment work."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from ipaddress import ip_address, ip_network
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse
import re


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    warnings: tuple[str, ...] = ()
    facts: dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationPolicy:
    allowed_methods: set[str] = field(default_factory=lambda: {"GET", "HEAD"})
    max_timeout: float = 60.0
    min_delay: float = 0.0
    max_delay: float = 30.0
    max_body_bytes: int = 10_000_000
    require_authorization: bool = True
    allow_private_targets: bool = True
    allow_public_targets: bool = True
    prohibited_tokens: tuple[str, ...] = (
        "brute", "password", "credential", "hydra", "medusa", "sqlmap", "exploit", "payload", "shell", "ransom", "flood", "ddos", "counter",
    )

    def validate_scan(self, target: str, timeout: float, delay: float, body_bytes: int, method: str = "GET") -> PolicyDecision:
        warnings: list[str] = []
        if method.upper() not in self.allowed_methods:
            return PolicyDecision(False, f"HTTP method {method} is not allowed")
        if not 0.5 <= timeout <= self.max_timeout:
            return PolicyDecision(False, f"timeout must be between 0.5 and {self.max_timeout}")
        if not self.min_delay <= delay <= self.max_delay:
            return PolicyDecision(False, f"delay must be between {self.min_delay} and {self.max_delay}")
        if not 1024 <= body_bytes <= self.max_body_bytes:
            return PolicyDecision(False, f"body limit must be between 1024 and {self.max_body_bytes}")
        try:
            parsed = urlparse(target if "://" in target else "https://" + target)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                return PolicyDecision(False, "target must be an http(s) URL")
            host = parsed.hostname
            private = self._is_private(host)
            if private and not self.allow_private_targets: return PolicyDecision(False, "private targets are disabled by policy")
            if not private and not self.allow_public_targets: return PolicyDecision(False, "public targets are disabled by policy")
            if parsed.scheme == "http": warnings.append("target is not using HTTPS")
            if parsed.port and parsed.port not in {80, 443, 8000, 8080, 8443}:
                warnings.append(f"non-standard port {parsed.port}")
            return PolicyDecision(True, "operation parameters are allowed", tuple(warnings), {"host": host, "private": private, "scheme": parsed.scheme})
        except ValueError as exc:
            return PolicyDecision(False, str(exc))

    @staticmethod
    def _is_private(host: str) -> bool:
        if host in {"localhost", "localhost.localdomain"}: return True
        try: return ip_address(host).is_private or ip_address(host).is_loopback or ip_address(host).is_link_local
        except ValueError: return host.endswith((".local", ".internal", ".test"))

    def validate_command_label(self, label: str) -> PolicyDecision:
        normalized = label.lower()
        hits = tuple(token for token in self.prohibited_tokens if token in normalized)
        if hits: return PolicyDecision(False, "operation label contains prohibited capability tokens", hits)
        return PolicyDecision(True, "label allowed")


class ScopePolicy:
    def __init__(self, rules: Iterable[dict[str, Any]]) -> None:
        self.rules = list(rules)

    def explain(self, target: str) -> PolicyDecision:
        value = target.strip().lower().rstrip("/")
        parsed = urlparse(value if "://" in value else "https://" + value)
        host = (parsed.hostname or "").lower()
        included_matches: list[str] = []
        excluded_matches: list[str] = []
        for rule in self.rules:
            rule_value = str(rule.get("value", "")).lower().strip().rstrip("/")
            if self.matches(rule_value, value, host, parsed.netloc.lower()):
                (included_matches if rule.get("included", True) else excluded_matches).append(rule_value)
        if excluded_matches: return PolicyDecision(False, "target matches an excluded scope rule", facts={"excluded": excluded_matches, "included": included_matches})
        if included_matches: return PolicyDecision(True, "target matches an included scope rule", facts={"included": included_matches})
        return PolicyDecision(False, "target does not match any included scope rule")

    @staticmethod
    def matches(rule: str, candidate: str, host: str, netloc: str) -> bool:
        if not rule: return False
        if rule.startswith(("http://", "https://")): return candidate.startswith(rule)
        if rule.startswith("*."): return host.endswith(rule[1:])
        if rule == host or rule == netloc: return True
        if "/" in rule and not rule.startswith("http"):
            try: return ip_address(host) in ip_network(rule, strict=False)
            except ValueError: pass
        return host.endswith("." + rule)


class FindingPolicy:
    transitions = {
        "draft": {"open"},
        "open": {"accepted", "remediated", "closed"},
        "accepted": {"remediated", "closed"},
        "remediated": {"verified", "open"},
        "verified": {"closed", "open"},
        "closed": {"open"},
    }
    severities = {"info", "low", "medium", "high", "critical"}
    required_for_high = ("impact", "remediation")

    def validate(self, finding: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for key in ("title", "summary", "affected_asset"):
            if not str(finding.get(key, "")).strip(): errors.append(f"{key} is required")
        severity = str(finding.get("severity", ""))
        if severity not in self.severities: errors.append("severity is invalid")
        cvss = finding.get("cvss")
        if cvss is not None:
            try:
                if not 0 <= float(cvss) <= 10: errors.append("cvss must be between 0 and 10")
            except (TypeError, ValueError): errors.append("cvss must be numeric")
        if severity in {"high", "critical"}:
            for key in self.required_for_high:
                if not str(finding.get(key, "")).strip(): errors.append(f"{key} is required for {severity} findings")
        return errors

    def can_transition(self, current: str, new: str) -> PolicyDecision:
        if new in self.transitions.get(current, set()): return PolicyDecision(True, "transition allowed")
        return PolicyDecision(False, f"transition {current} -> {new} is not allowed")


class DataPolicy:
    sensitive_keys = {"password", "passwd", "secret", "token", "api_key", "private_key", "authorization"}

    def redact(self, value: Any) -> Any:
        if isinstance(value, dict): return {key: "[REDACTED]" if key.lower() in self.sensitive_keys else self.redact(item) for key, item in value.items()}
        if isinstance(value, list): return [self.redact(item) for item in value]
        if isinstance(value, str):
            value = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._-]+", r"\1[REDACTED]", value)
            value = re.sub(r"(?i)(password|token|secret)=([^&\s]+)", r"\1=[REDACTED]", value)
        return value

    def validate_evidence(self, title: str, content: str) -> list[str]:
        errors: list[str] = []
        if not title.strip(): errors.append("evidence title is required")
        if not content.strip(): errors.append("evidence content is required")
        if len(content.encode("utf-8")) > 10_000_000: errors.append("evidence exceeds 10 MB")
        return errors


@dataclass
class PolicyReport:
    checks: list[PolicyDecision]

    @property
    def allowed(self) -> bool: return all(item.allowed for item in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {"allowed": self.allowed, "checks": [{"allowed": item.allowed, "reason": item.reason, "warnings": list(item.warnings), "facts": item.facts} for item in self.checks]}


def validate_operation(target: str, scope_rules: Iterable[dict[str, Any]], timeout: float, delay: float, max_body: int) -> PolicyReport:
    policy = OperationPolicy(); checks = [policy.validate_scan(target, timeout, delay, max_body), ScopePolicy(scope_rules).explain(target)]
    return PolicyReport(checks)
