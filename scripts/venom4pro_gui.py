#!/usr/bin/env python3
"""Launch the optional multi-panel desktop GUI."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    try:
        from bgxdesk.main import main as gui_main
    except ModuleNotFoundError as exc:
        if exc.name == "PySide6":
            print("PySide6 belum terpasang. Jalankan ./install_venom4.sh lalu ulangi ./run.sh gui.", file=sys.stderr)
            return 2
        raise
    gui_main()
    return 0


if __name__ == "__main__": raise SystemExit(main())
