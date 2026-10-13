from __future__ import annotations

import argparse
from pathlib import Path

from bgxdesk.services.assessment import InventoryService, ReportService
from bgxdesk.services.scanner import ReadOnlyScanner, ScanConfig, scan_to_markdown
from bgxdesk.services.storage import JsonStore, Repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BGXTEAM Security Desk offline CLI")
    parser.add_argument("--project", default=str(Path.home() / ".local/share/bgxteam-security-desk/project.json"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show project counts")
    sub.add_parser("inventory", help="check local executable presence")
    export = sub.add_parser("export", help="export a report")
    export.add_argument("format", choices=("md", "csv", "json"))
    export.add_argument("output")
    scan = sub.add_parser("scan", help="run authorized read-only web checks")
    scan.add_argument("target")
    scan.add_argument("output", nargs="?")
    scan.add_argument("--timeout", type=float, default=8.0)
    scan.add_argument("--delay", type=float, default=0.6)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    repository = Repository(JsonStore(args.project))
    if args.command == "status":
        for key, value in repository.snapshot.counts().items(): print(f"{key}: {value}")
    elif args.command == "inventory":
        results = InventoryService(repository).check_all()
        for result in results: print(f"{result.name}: {'installed' if result.installed else 'not detected'} {result.version}")
    elif args.command == "export":
        service = ReportService(repository)
        path = {"md": service.export_markdown, "csv": service.export_csv, "json": service.export_json}[args.format](args.output)
        print(path)
    elif args.command == "scan":
        scanner = ReadOnlyScanner(repository, ScanConfig(timeout_seconds=args.timeout, delay_seconds=args.delay))
        result = scanner.run(args.target)
        print(result.to_json())
        if args.output:
            Path(args.output).expanduser().resolve().write_text(scan_to_markdown(result), encoding="utf-8")


if __name__ == "__main__": main()
