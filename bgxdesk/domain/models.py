"""Domain models for BGXTEAM Security Desk.

The module is intentionally offline-first. Models describe authorized assessment
work and do not execute network actions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from hashlib import sha256
from typing import Any, Iterable
import json
import re
import uuid
from urllib.parse import urlparse


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Policy(str, Enum):
    SAFE = "safe"
    REVIEW = "review"
    RESTRICTED = "restricted"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FindingStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    ACCEPTED = "accepted"
    REMEDIATED = "remediated"
    VERIFIED = "verified"
    CLOSED = "closed"


class AssetType(str, Enum):
    DOMAIN = "domain"
    URL = "url"
    IP = "ip"
    API = "api"
    MOBILE = "mobile"
    REPOSITORY = "repository"
    OTHER = "other"


@dataclass
class ScopeRule:
    value: str
    kind: AssetType = AssetType.OTHER
    included: bool = True
    notes: str = ""

    def normalized(self) -> str:
        return self.value.strip().lower()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.value.strip():
            errors.append("Scope value cannot be empty")
        if len(self.value) > 512:
            errors.append("Scope value is too long")
        if "\n" in self.value or "\r" in self.value:
            errors.append("Scope value cannot contain newlines")
        return errors


@dataclass
class AuthorizationRecord:
    client: str
    engagement: str
    reviewer: str
    start_at: str
    end_at: str
    emergency_contact: str
    rules: list[ScopeRule] = field(default_factory=list)
    approved_methods: list[str] = field(default_factory=list)
    prohibited_methods: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=utc_now)
    active: bool = True

    def validate(self) -> list[str]:
        errors: list[str] = []
        for name, value in (("client", self.client), ("engagement", self.engagement), ("reviewer", self.reviewer), ("start_at", self.start_at), ("end_at", self.end_at), ("emergency_contact", self.emergency_contact)):
            if not value.strip():
                errors.append(f"{name} is required")
        if not self.rules:
            errors.append("At least one scope rule is required")
        for index, rule in enumerate(self.rules):
            errors.extend(f"rules[{index}]: {error}" for error in rule.validate())
        if not self.approved_methods:
            errors.append("At least one approved method is required")
        return errors

    def is_in_scope(self, target: str) -> bool:
        candidate = target.strip().lower().rstrip("/")
        matches_include = any(rule.included and self._matches(rule.normalized(), candidate) for rule in self.rules)
        matches_exclude = any(not rule.included and self._matches(rule.normalized(), candidate) for rule in self.rules)
        return matches_include and not matches_exclude

    @staticmethod
    def _matches(rule: str, candidate: str) -> bool:
        if rule == candidate:
            return True
        parsed = urlparse(candidate)
        candidate_netloc = parsed.netloc.lower()
        candidate_host = (parsed.hostname or "").lower()
        if candidate_netloc and rule in {candidate_netloc, candidate_host}:
            return True
        if rule.startswith("*."):
            host = candidate_host or candidate
            return host.endswith(rule[1:])
        if rule.startswith("https://") or rule.startswith("http://"):
            return candidate.startswith(rule)
        host = candidate_host or candidate
        return host.endswith("." + rule) or host == rule

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rules"] = [asdict(rule) for rule in self.rules]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuthorizationRecord":
        rules = [ScopeRule(value=item.get("value", ""), kind=AssetType(item.get("kind", "other")), included=bool(item.get("included", True)), notes=item.get("notes", "")) for item in data.get("rules", [])]
        values = {key: data.get(key, "") for key in ("client", "engagement", "reviewer", "start_at", "end_at", "emergency_contact")}
        return cls(**values, rules=rules, approved_methods=list(data.get("approved_methods", [])), prohibited_methods=list(data.get("prohibited_methods", [])), id=data.get("id", str(uuid.uuid4())), created_at=data.get("created_at", utc_now()), active=bool(data.get("active", True)))


@dataclass
class Asset:
    name: str
    asset_type: AssetType
    owner: str = ""
    environment: str = "production"
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    in_scope: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name.strip():
            errors.append("Asset name is required")
        if len(self.name) > 512:
            errors.append("Asset name is too long")
        if any(not tag.strip() for tag in self.tags):
            errors.append("Tags cannot be empty")
        return errors

    def touch(self) -> None:
        self.updated_at = utc_now()


@dataclass
class Evidence:
    title: str
    content: str
    source: str = "manual"
    checksum: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.checksum:
            self.checksum = sha256(self.content.encode("utf-8", errors="replace")).hexdigest()

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.title.strip():
            errors.append("Evidence title is required")
        if not self.content:
            errors.append("Evidence content is required")
        return errors


@dataclass
class Finding:
    title: str
    severity: Severity
    summary: str
    affected_asset: str
    reproduction: str = ""
    impact: str = ""
    remediation: str = ""
    references: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    status: FindingStatus = FindingStatus.DRAFT
    cvss: float | None = None
    assignee: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def validate(self) -> list[str]:
        errors: list[str] = []
        for name, value in (("title", self.title), ("summary", self.summary), ("affected_asset", self.affected_asset)):
            if not value.strip():
                errors.append(f"{name} is required")
        if self.cvss is not None and not 0 <= self.cvss <= 10:
            errors.append("CVSS must be between 0 and 10")
        if self.severity in {Severity.HIGH, Severity.CRITICAL} and not self.impact.strip():
            errors.append("Impact is required for high and critical findings")
        return errors

    def transition(self, new_status: FindingStatus) -> None:
        allowed = {
            FindingStatus.DRAFT: {FindingStatus.OPEN},
            FindingStatus.OPEN: {FindingStatus.ACCEPTED, FindingStatus.REMEDIATED, FindingStatus.CLOSED},
            FindingStatus.ACCEPTED: {FindingStatus.REMEDIATED, FindingStatus.CLOSED},
            FindingStatus.REMEDIATED: {FindingStatus.VERIFIED, FindingStatus.OPEN},
            FindingStatus.VERIFIED: {FindingStatus.CLOSED, FindingStatus.OPEN},
            FindingStatus.CLOSED: {FindingStatus.OPEN},
        }
        if new_status not in allowed[self.status]:
            raise ValueError(f"Invalid finding transition: {self.status.value} -> {new_status.value}")
        self.status = new_status
        self.updated_at = utc_now()

    def as_markdown(self) -> str:
        refs = "\n".join(f"- {ref}" for ref in self.references) or "- None provided"
        evidence = "\n".join(f"- {item}" for item in self.evidence_ids) or "- None attached"
        score = "Not scored" if self.cvss is None else f"{self.cvss:.1f}"
        return f"## {self.title}\n\n- **Severity:** {self.severity.value.upper()}\n- **CVSS:** {score}\n- **Status:** {self.status.value}\n- **Affected asset:** `{self.affected_asset}`\n- **Assignee:** {self.assignee or 'Unassigned'}\n\n### Summary\n{self.summary}\n\n### Reproduction\n{self.reproduction or 'Not documented.'}\n\n### Impact\n{self.impact or 'Not documented.'}\n\n### Remediation\n{self.remediation or 'Not documented.'}\n\n### Evidence\n{evidence}\n\n### References\n{refs}\n"


@dataclass
class AuditEvent:
    action: str
    entity: str
    entity_id: str = ""
    actor: str = "local-user"
    details: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


@dataclass
class ToolRecord:
    name: str
    category: str
    purpose: str
    executable: str
    policy: Policy = Policy.REVIEW
    aliases: list[str] = field(default_factory=list)
    documentation_url: str = ""
    installed: bool = False
    version: str = ""
    last_checked: str = ""

    def all_executables(self) -> list[str]:
        return list(dict.fromkeys([self.executable, *self.aliases]))

    def policy_label(self) -> str:
        return self.policy.value.upper()


@dataclass
class ProjectSnapshot:
    authorizations: list[AuthorizationRecord] = field(default_factory=list)
    assets: list[Asset] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    events: list[AuditEvent] = field(default_factory=list)
    tools: list[ToolRecord] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {"authorizations": len(self.authorizations), "assets": len(self.assets), "findings": len(self.findings), "evidence": len(self.evidence), "events": len(self.events), "tools": len(self.tools)}

    def finding_counts(self) -> dict[str, int]:
        return {severity.value: sum(item.severity == severity for item in self.findings) for severity in Severity}

    def validate(self) -> list[str]:
        errors: list[str] = []
        for collection_name in ("authorizations", "assets", "findings", "evidence"):
            collection = getattr(self, collection_name)
            for index, item in enumerate(collection):
                if hasattr(item, "validate"):
                    errors.extend(f"{collection_name}[{index}]: {error}" for error in item.validate())
        return errors


def enum_value(value: Enum | str) -> str:
    return value.value if isinstance(value, Enum) else str(value)


def json_default(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "__dict__"):
        return value.__dict__
    raise TypeError(f"Unsupported value: {type(value)!r}")


def dump_model(value: Any) -> str:
    return json.dumps(value, default=json_default, indent=2, ensure_ascii=False)


def normalize_tags(tags: Iterable[str]) -> list[str]:
    result: list[str] = []
    for tag in tags:
        clean = re.sub(r"\s+", "-", tag.strip().lower())
        if clean and clean not in result:
            result.append(clean)
    return result
