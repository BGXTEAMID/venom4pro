#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bgxdesk.services.inventory import EnvironmentDoctor, InventoryService
from bgxdesk.services.sqlite_store import SQLiteStore
from bgxdesk.services.project_ops import ProjectMaintenance
from bgxdesk.services.reporting import ReportBuilder


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="venom4pro-doctor", description="Inspect local Kali runtime without touching targets")
    parser.add_argument("--db", default=None)
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("environment"); sub.add_parser("tools"); sub.add_parser("database"); sub.add_parser("metrics")
    return parser


def main() -> int:
    args = make_parser().parse_args(); store = SQLiteStore(args.db)
    if args.command == "environment": result = EnvironmentDoctor().run()
    elif args.command == "tools":
        inventory = InventoryService(); statuses = inventory.scan(); result = {"summary": inventory.summary(statuses), "tools": [status.as_dict() for status in statuses]}
    elif args.command == "database": result = ProjectMaintenance(store).integrity_check()
    else: result = ReportBuilder(store).metrics()
    if args.json: print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(f"Venom4pro doctor: {args.command}")
        if isinstance(result, dict):
            for key, value in result.items(): print(f"- {key}: {value if not isinstance(value, (dict, list)) else json.dumps(value, ensure_ascii=False)}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
