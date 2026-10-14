"""Output formatting helpers for terminal operators."""
from __future__ import annotations

from typing import Any, Iterable, Sequence
import json
import textwrap


class TerminalFormatter:
    def __init__(self, color: bool = True, width: int = 120) -> None: self.color = color; self.width = max(40, width)

    def colorize(self, text: str, tone: str) -> str:
        if not self.color: return text
        colors = {"green": "\033[92m", "red": "\033[91m", "yellow": "\033[93m", "cyan": "\033[96m", "gray": "\033[90m", "reset": "\033[0m"}; return colors.get(tone, "") + text + colors["reset"]

    def status(self, value: str) -> str:
        tone = "green" if value in {"completed", "ok", "installed", "verified"} else "red" if value in {"failed", "rejected", "critical", "missing"} else "yellow" if value in {"warning", "finding", "open", "queued"} else "cyan"; return self.colorize(value.upper(), tone)

    def table(self, rows: Iterable[dict[str, Any]], columns: Sequence[str], headers: Sequence[str] | None = None) -> str:
        values = [[str(row.get(column, "")) for column in columns] for row in rows]; labels = list(headers or columns); widths = [len(label) for label in labels]
        for row in values:
            for index, value in enumerate(row): widths[index] = min(max(widths[index], len(value)), max(12, self.width // max(1, len(columns))))
        def line(items: Sequence[str]) -> str: return " | ".join(value[:widths[index]].ljust(widths[index]) for index, value in enumerate(items))
        result = [line(labels), "-+-".join("-" * width for width in widths)]; result.extend(line(row) for row in values); return "\n".join(result)

    def bullets(self, values: Iterable[Any], prefix: str = "- ") -> str: return "\n".join(prefix + str(value) for value in values)

    def wrapped(self, text: str, indent: int = 2) -> str: return textwrap.fill(text, width=self.width, initial_indent=" " * indent, subsequent_indent=" " * indent)

    def json(self, value: Any, pretty: bool = True) -> str: return json.dumps(value, ensure_ascii=False, indent=2 if pretty else None, default=str)

    def jsonl(self, values: Iterable[Any]) -> str: return "".join(json.dumps(value, ensure_ascii=False, default=str) + "\n" for value in values)

    def report_header(self, title: str, subtitle: str = "") -> str:
        bar = "=" * min(self.width, max(len(title), 20)); return f"{bar}\n{title}\n{bar}\n{subtitle}\n" if subtitle else f"{bar}\n{title}\n{bar}\n"
