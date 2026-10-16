#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bgxdesk.services.migrations import MigrationManager
from bgxdesk.services.sqlite_store import SQLiteStore


def main() -> int:
    parser = argparse.ArgumentParser(prog="venom4pro-migrate"); parser.add_argument("--db", default=None); parser.add_argument("command", choices=("status", "apply", "verify")); args = parser.parse_args(); manager = MigrationManager(SQLiteStore(args.db)); result = manager.status() if args.command == "status" else manager.apply() if args.command == "apply" else manager.verify(); print(json.dumps(result, indent=2, ensure_ascii=False)); return 0


if __name__ == "__main__": raise SystemExit(main())
