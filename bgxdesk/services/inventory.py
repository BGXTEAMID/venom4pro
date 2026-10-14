"""Local tool inventory and environment diagnostics.

Only executable presence and version/help metadata are inspected. No target
is contacted and no tool command is launched with user-provided arguments.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from typing import Iterable
import os
import platform
import subprocess


@dataclass(frozen=True)
class ToolSpec:
    name: str
    category: str
    executable: str
    purpose: str
    policy: str = "review"
    aliases: tuple[str, ...] = ()
    check_args: tuple[str, ...] = ("--version",)

    def candidates(self) -> tuple[str, ...]: return tuple(dict.fromkeys((self.executable, *self.aliases)))


@dataclass
class ToolStatus:
    name: str
    category: str
    executable: str
    purpose: str
    policy: str
    installed: bool
    path: str = ""
    version: str = ""
    error: str = ""
    checked_at: str = ""

    def as_dict(self) -> dict: return asdict(self)


DEFAULT_CATALOG: tuple[ToolSpec, ...] = (
    ToolSpec("python", "Runtime", "python3", "Python interpreter", "safe", ("python",)),
    ToolSpec("sqlite", "Database", "sqlite3", "SQLite command line client", "safe"),
    ToolSpec("git", "Project", "git", "Version control", "safe"),
    ToolSpec("curl", "HTTP Diagnostics", "curl", "Local HTTP metadata utility", "review"),
    ToolSpec("wget", "HTTP Diagnostics", "wget", "Local HTTP download utility", "review"),
    ToolSpec("nmap", "Network Discovery", "nmap", "Authorized network inventory", "review"),
    ToolSpec("httpx", "Web Assessment", "httpx", "HTTP metadata inspection", "review"),
    ToolSpec("nuclei", "Web Assessment", "nuclei", "Template checks; separate review required", "restricted"),
    ToolSpec("ffuf", "Content Discovery", "ffuf", "Content discovery; separate review required", "restricted"),
    ToolSpec("burpsuite", "Web Assessment", "burpsuite", "Intercepting proxy", "review", ("burp",)),
    ToolSpec("zaproxy", "Web Assessment", "zaproxy", "Web proxy scanner", "review", ("zap",)),
    ToolSpec("wireshark", "Traffic Analysis", "wireshark", "Packet analysis GUI", "safe"),
    ToolSpec("tcpdump", "Traffic Analysis", "tcpdump", "Packet capture inspection", "safe"),
    ToolSpec("semgrep", "Code Security", "semgrep", "Static source analysis", "safe"),
    ToolSpec("bandit", "Code Security", "bandit", "Python source security linting", "safe"),
    ToolSpec("pip-audit", "Dependency", "pip-audit", "Python dependency audit", "safe"),
    ToolSpec("trivy", "Container", "trivy", "Filesystem/image audit", "review"),
    ToolSpec("jadx", "Mobile", "jadx", "Android decompiler", "safe"),
    ToolSpec("apktool", "Mobile", "apktool", "Android package inspection", "safe"),
    ToolSpec("adb", "Mobile", "adb", "Android debugging bridge", "review"),
    ToolSpec("ghidra", "Reverse Engineering", "ghidra", "Binary analysis suite", "safe"),
    ToolSpec("r2", "Reverse Engineering", "r2", "Reverse engineering toolkit", "safe", ("radare2",)),
    ToolSpec("gdb", "Debugging", "gdb", "GNU debugger", "safe"),
)


class InventoryService:
    def __init__(self, catalog: Iterable[ToolSpec] = DEFAULT_CATALOG) -> None: self.catalog = tuple(catalog)

    def check(self, spec: ToolSpec, timeout: float = 3.0) -> ToolStatus:
        checked = datetime.now(timezone.utc).isoformat(timespec="seconds"); path = next((which(candidate) for candidate in spec.candidates() if which(candidate)), None)
        if not path: return ToolStatus(spec.name, spec.category, spec.executable, spec.purpose, spec.policy, False, checked_at=checked)
        version = ""; error = ""
        try:
            result = subprocess.run([path, *spec.check_args], capture_output=True, text=True, timeout=timeout, check=False)
            raw = (result.stdout or result.stderr).strip(); version = raw.splitlines()[0][:240] if raw else f"exit {result.returncode}"
        except (OSError, subprocess.TimeoutExpired) as exc: error = str(exc)
        return ToolStatus(spec.name, spec.category, spec.executable, spec.purpose, spec.policy, True, path, version, error, checked)

    def scan(self, timeout: float = 3.0) -> list[ToolStatus]: return [self.check(spec, timeout) for spec in self.catalog]

    def installed(self, timeout: float = 3.0) -> list[ToolStatus]: return [status for status in self.scan(timeout) if status.installed]

    def missing(self, timeout: float = 3.0) -> list[ToolStatus]: return [status for status in self.scan(timeout) if not status.installed]

    def by_category(self, statuses: Iterable[ToolStatus]) -> dict[str, list[ToolStatus]]:
        grouped: dict[str, list[ToolStatus]] = {}
        for status in statuses: grouped.setdefault(status.category, []).append(status)
        return grouped

    def summary(self, statuses: Iterable[ToolStatus]) -> dict:
        items = list(statuses); return {"total": len(items), "installed": sum(item.installed for item in items), "missing": sum(not item.installed for item in items), "categories": len({item.category for item in items}), "restricted_installed": sum(item.installed and item.policy == "restricted" for item in items)}


class EnvironmentDoctor:
    def __init__(self, inventory: InventoryService | None = None) -> None: self.inventory = inventory or InventoryService()

    def python(self) -> dict:
        return {"version": platform.python_version(), "implementation": platform.python_implementation(), "executable": os.path.abspath(os.sys.executable), "platform": platform.platform()}

    def directories(self, paths: Iterable[str | Path]) -> list[dict]:
        result = []
        for value in paths:
            path = Path(value).expanduser(); result.append({"path": str(path), "exists": path.exists(), "directory": path.is_dir(), "writable": os.access(path, os.W_OK) if path.exists() else os.access(path.parent, os.W_OK)})
        return result

    def run(self) -> dict:
        statuses = self.inventory.scan(); return {"python": self.python(), "inventory": self.inventory.summary(statuses), "tools": [item.as_dict() for item in statuses], "directories": self.directories((Path.home() / ".local/share/venom4pro", Path.cwd()))}
