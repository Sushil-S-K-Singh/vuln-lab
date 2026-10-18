#!/usr/bin/env bash
# Start the VULNLAB server
set -e
cd "$(dirname "$0")"
if [ ! -f vulnlab.db ]; then
  echo "[*] initializing database..."
  python3 init_db.py
fi
echo "[*] starting VULNLAB on http://0.0.0.0:8000"
python3 app.py
