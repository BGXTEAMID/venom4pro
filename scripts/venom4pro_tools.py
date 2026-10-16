#!/usr/bin/env python3
"""Inspect the curated security-tool catalog without executing tools."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from shutil import which
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bgxdesk.services.tool_catalog import categories, category_counts, count, find, to_jsonable


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="venom4pro-tools", description="600+ security tool catalog with safe inspection commands")
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("summary", help="show catalog size and categories")
    listing = sub.add_parser("list", help="list catalog entries")
    listing.add_argument("--query", default=""); listing.add_argument("--category", default=None); listing.add_argument("--risk", choices=("safe", "review", "restricted"), default=None); listing.add_argument("--limit", type=int, default=100); listing.add_argument("--commands", action="store_true")
    export = sub.add_parser("export", help="export catalog JSON")
    export.add_argument("output"); export.add_argument("--query", default=""); export.add_argument("--category", default=None); export.add_argument("--risk", default=None)
    plan = sub.add_parser("install-plan", help="write a non-executing apt/package plan")
    plan.add_argument("output"); plan.add_argument("--category", default=None)
    check = sub.add_parser("check", help="check executable presence only")
    check.add_argument("--query", default=""); check.add_argument("--category", default=None); check.add_argument("--limit", type=int, default=100)
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "summary":
        print(json.dumps({"tools": count(), "categories": categories(), "category_counts": category_counts()}, ensure_ascii=False, indent=2)); return 0
    entries = find(getattr(args, "query", ""), getattr(args, "category", None), getattr(args, "risk", None))
    if args.command == "list":
        values = []
        for entry in entries[:max(1, min(args.limit, 5000))]:
            value = entry.as_dict()
            if not args.commands: value.pop("safe_commands", None)
            values.append(value)
        print(json.dumps(values, ensure_ascii=False, indent=2)); return 0
    if args.command == "export":
        output = Path(args.output).expanduser().resolve(); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(to_jsonable(entries), ensure_ascii=False, indent=2), encoding="utf-8"); print(json.dumps({"path": str(output), "count": len(entries)}, indent=2)); return 0
    if args.command == "install-plan":
        packages = sorted({entry.package for entry in entries if entry.family == "apt"}); output = Path(args.output).expanduser().resolve(); output.parent.mkdir(parents=True, exist_ok=True); lines = ["# Non-executing package plan", "# Review each package before installation.", "", "sudo apt update", "sudo apt install -y \\"] + [f"  {package}{' \\' if index < len(packages)-1 else ''}" for index, package in enumerate(packages)]
        output.write_text("\n".join(lines) + "\n", encoding="utf-8"); print(json.dumps({"path": str(output), "apt_packages": len(packages)}, indent=2)); return 0
    if args.command == "check":
        result = []
        for entry in entries[:max(1, min(args.limit, 5000))]: result.append({"name": entry.name, "command": entry.command, "category": entry.category, "risk": entry.risk, "installed": bool(which(entry.command)), "path": which(entry.command) or "", "safe_commands": entry.safe_commands()})
        print(json.dumps({"checked": len(result), "installed": sum(item["installed"] for item in result), "items": result}, ensure_ascii=False, indent=2)); return 0
    return 2


if __name__ == "__main__": raise SystemExit(main())
