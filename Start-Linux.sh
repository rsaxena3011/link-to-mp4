#!/bin/sh
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ is required. Install it with your package manager, for example:"
  echo "  Debian/Ubuntu: sudo apt install python3 python3-venv python3-pip"
  echo "  Fedora:        sudo dnf install python3"
  echo "  Arch:          sudo pacman -S python"
  exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "Your Python is older than 3.10. Install a newer Python with your package manager."
  exit 1
fi
python3 App/app.py "$@"
