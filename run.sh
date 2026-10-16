#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo "Environment belum ada. Jalankan ./install_venom4.sh terlebih dahulu." >&2
  exit 1
fi
if [[ "${1:-}" == "gui" ]]; then
  shift
  exec .venv/bin/python scripts/venom4pro_gui.py "$@"
fi
exec .venv/bin/python venom4.py "$@"
