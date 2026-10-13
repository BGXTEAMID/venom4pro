#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3 python3-venv python3-pip python3-dev
fi

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
chmod +x venom4.py install_venom4.sh
printf '\nInstalled. Run GUI: ./.venv/bin/python venom4.py\n'
printf 'CLI status: ./.venv/bin/python -m bgxdesk.cli status\n'
printf 'CLI scan: ./.venv/bin/python -m bgxdesk.cli scan <authorized-url> report.md\n'
