from pathlib import Path

import pytest

from bgxdesk.domain.models import Asset, AssetType, AuthorizationRecord, Finding, FindingStatus, ScopeRule, Severity
from bgxdesk.services.assessment import AuthorizationService, FindingsService
from bgxdesk.services.storage import JsonStore, Repository


def make_repo(tmp_path: Path) -> Repository:
    return Repository(JsonStore(tmp_path / "project.json"))


def test_scope_include_exclude(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    record = AuthorizationRecord("Client", "Test", "Reviewer", "start", "end", "contact", [ScopeRule("example.com"), ScopeRule("admin.example.com", included=False)], ["manual review"])
    AuthorizationService(repo).create(record)
    service = AuthorizationService(repo)
    assert service.check_target("app.example.com")[0]
    assert not service.check_target("admin.example.com")[0]


def test_finding_transition(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    service = FindingsService(repo)
    item = service.create(Finding("Test", Severity.LOW, "Summary", "app.example.com"))
    service.transition(item.id, FindingStatus.OPEN)
    assert repo.get("findings", item.id).status == FindingStatus.OPEN
    with pytest.raises(ValueError): service.transition(item.id, FindingStatus.VERIFIED)


def test_persistence_roundtrip(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    repo.snapshot.assets.append(Asset("app.example.com", AssetType.DOMAIN))
    repo.save()
    loaded = make_repo(tmp_path)
    assert loaded.snapshot.assets[0].name == "app.example.com"
