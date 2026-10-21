#!/bin/sh
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Install Python 3.10+, venv and pip with your distribution's package manager."
  exit 1
fi
python3 App/app.py "$@"
