#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip python3-dev sqlite3
fi
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
chmod +x venom4.py run.sh install_venom4.sh scripts/venom4pro.py scripts/venom4pro_gui.py
./run.sh init
printf '\nSetup selesai. Contoh: ./run.sh status\n'
