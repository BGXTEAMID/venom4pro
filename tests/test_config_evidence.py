from pathlib import Path
from tempfile import TemporaryDirectory

from bgxdesk.services.config import ConfigService, RuntimeConfig
from bgxdesk.services.evidence import EvidenceService
from bgxdesk.services.sqlite_store import SQLiteStore


def test_config_roundtrip() -> None:
    with TemporaryDirectory() as folder:
        path = Path(folder) / "config.json"; service = ConfigService(path); config = RuntimeConfig(database_path=str(Path(folder) / "db.sqlite"), default_delay=1.2); service.save(config); loaded = ConfigService(path).load(); assert loaded.default_delay == 1.2; assert loaded.validate() == []


def test_evidence_checksum_and_attachment() -> None:
    with TemporaryDirectory() as folder:
        store = SQLiteStore(Path(folder) / "db.sqlite"); finding = store.add_finding({"title": "Evidence", "severity": "low", "summary": "Summary", "affected_asset": "local"}); service = EvidenceService(store, Path(folder) / "evidence"); item = service.add_text("Request", "Authorization: Bearer secret", redact=True); assert service.verify(item.id)["match"]; updated = service.attach_to_finding(finding["id"], item.id); assert item.id in updated["evidence_ids"]
