#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bgxdesk.services.project_ops import ProjectMaintenance
from bgxdesk.services.reporting import ReportBuilder
from bgxdesk.services.sqlite_store import SQLiteStore


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="venom4pro-admin", description="SQLite maintenance for Venom4pro Kali script mode")
    root.add_argument("--db", default=None)
    sub = root.add_subparsers(dest="command", required=True)
    for command in ("integrity", "vacuum"): sub.add_parser(command)
    backup = sub.add_parser("backup"); backup.add_argument("destination")
    restore = sub.add_parser("restore"); restore.add_argument("source"); restore.add_argument("--no-before-backup", action="store_true")
    export = sub.add_parser("export"); export.add_argument("destination")
    imp = sub.add_parser("import"); imp.add_argument("source"); imp.add_argument("--replace", action="store_true")
    report = sub.add_parser("report"); report.add_argument("destination"); report.add_argument("--format", choices=("md", "csv", "json"), default=None)
    return root


def main() -> int:
    args = parser().parse_args(); store = SQLiteStore(args.db); maintenance = ProjectMaintenance(store)
    if args.command == "integrity": result = maintenance.integrity_check()
    elif args.command == "vacuum": result = maintenance.vacuum()
    elif args.command == "backup": result = maintenance.backup(args.destination)
    elif args.command == "restore": result = maintenance.restore(args.source, create_backup=not args.no_before_backup)
    elif args.command == "export": result = {"path": str(maintenance.export_json(args.destination))}
    elif args.command == "import": result = maintenance.import_json(args.source, replace=args.replace)
    elif args.command == "report": result = {"path": str(ReportBuilder(store).write(args.destination, args.format))}
    else: raise RuntimeError(args.command)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str)); return 0


if __name__ == "__main__": raise SystemExit(main())
