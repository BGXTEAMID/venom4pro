#!/usr/bin/env python3
"""Run bounded read-only scans from a local target file.

Every line is normalized, checked against the active authorization, scanned
sequentially, and persisted to SQLite. Blank lines and comments are ignored.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bgxdesk.services.sqlite_store import SQLiteStore
from scripts.venom4pro import scan, build_parser


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="venom4pro-batch")
    root.add_argument("targets_file"); root.add_argument("--db", default=None); root.add_argument("--delay", type=float, default=1.0); root.add_argument("--timeout", type=float, default=8.0); root.add_argument("--max-body", type=int, default=512000); root.add_argument("--stop-on-error", action="store_true"); root.add_argument("--output", default="batch-results.json")
    return root


def read_targets(path: str) -> list[str]:
    values = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if value and not value.startswith("#") and value not in values: values.append(value)
    return values


def main() -> int:
    args = parser().parse_args(); store = SQLiteStore(args.db); results = []
    for target in read_targets(args.targets_file):
        scan_args = argparse.Namespace(target=target, delay=args.delay, timeout=args.timeout, max_body=args.max_body, robots=True, sitemap=True, openapi=True, verify_tls=True)
        try: result = scan(store, scan_args)
        except (PermissionError, ValueError, OSError) as exc:
            result = {"target": target, "status": "rejected", "error": str(exc)}
            if args.stop_on_error: results.append(result); break
        results.append(result)
    output = Path(args.output).expanduser().resolve(); output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps({"targets": len(results), "results": results}, ensure_ascii=False, indent=2), encoding="utf-8"); print(json.dumps({"targets": len(results), "output": str(output), "completed": sum(item.get("status") == "completed" for item in results), "rejected": sum(item.get("status") == "rejected" for item in results)}, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
