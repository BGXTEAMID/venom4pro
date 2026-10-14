"""Configuration loading and validation for Kali script mode."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any
import json
import os


@dataclass
class RuntimeConfig:
    database_path: str = "~/.local/share/venom4pro/venom4pro.db"
    default_timeout: float = 8.0
    default_delay: float = 0.6
    default_max_body: int = 512000
    verify_tls: bool = True
    allow_public_targets: bool = True
    allow_private_targets: bool = True
    user_agent: str = "Venom4pro/3.0 Kali authorized-read-only"
    report_directory: str = "./reports"
    backup_directory: str = "./backups"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not 0.5 <= self.default_timeout <= 60: errors.append("default_timeout must be between 0.5 and 60")
        if not 0 <= self.default_delay <= 30: errors.append("default_delay must be between 0 and 30")
        if not 1024 <= self.default_max_body <= 10_000_000: errors.append("default_max_body is outside safe range")
        if not self.user_agent.strip(): errors.append("user_agent cannot be empty")
        return errors

    def expanded_database_path(self) -> Path: return Path(os.path.expanduser(self.database_path)).resolve()

    def as_dict(self) -> dict[str, Any]: return asdict(self)


class ConfigService:
    def __init__(self, path: str | Path | None = None) -> None: self.path = Path(path).expanduser().resolve() if path else None

    def load(self) -> RuntimeConfig:
        config = RuntimeConfig()
        if self.path and self.path.exists():
            raw = json.loads(self.path.read_text(encoding="utf-8")); known = {field.name for field in fields(RuntimeConfig)}; config = RuntimeConfig(**{key: value for key, value in raw.items() if key in known})
        env_map = {"VENOM4PRO_DB": "database_path", "VENOM4PRO_TIMEOUT": "default_timeout", "VENOM4PRO_DELAY": "default_delay", "VENOM4PRO_MAX_BODY": "default_max_body", "VENOM4PRO_REPORT_DIR": "report_directory", "VENOM4PRO_BACKUP_DIR": "backup_directory"}
        values = config.as_dict()
        for env_name, field_name in env_map.items():
            if env_name in os.environ:
                value: Any = os.environ[env_name]
                if field_name in {"default_timeout", "default_delay"}: value = float(value)
                if field_name == "default_max_body": value = int(value)
                values[field_name] = value
        config = RuntimeConfig(**values); errors = config.validate()
        if errors: raise ValueError("; ".join(errors))
        return config

    def save(self, config: RuntimeConfig) -> Path:
        errors = config.validate()
        if errors: raise ValueError("; ".join(errors))
        destination = self.path or Path("venom4pro.config.json"); destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text(json.dumps(config.as_dict(), indent=2), encoding="utf-8"); return destination

    def init_defaults(self) -> Path:
        config = self.load(); config.expanded_database_path().parent.mkdir(parents=True, exist_ok=True); Path(config.report_directory).expanduser().mkdir(parents=True, exist_ok=True); Path(config.backup_directory).expanduser().mkdir(parents=True, exist_ok=True); return self.save(config)
