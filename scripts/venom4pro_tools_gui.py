#!/usr/bin/env python3
"""Launch the standalone Venom4pro Tool Catalog GUI."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    try:
        from bgxdesk.tool_catalog_gui import main as gui_main
    except ModuleNotFoundError as exc:
        if exc.name == "PySide6":
            print("PySide6 belum terpasang. Jalankan ./install_venom4.sh terlebih dahulu.", file=sys.stderr)
            return 2
        raise
    gui_main()
    return 0


if __name__ == "__main__": raise SystemExit(main())
