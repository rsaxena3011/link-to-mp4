#!/bin/sh
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ is required. Opening the official download page..."
  open "https://www.python.org/downloads/macos/" >/dev/null 2>&1
  echo "Install Python, then run Start-Mac.command again."
elif ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "Your Python is older than 3.10. Opening the official download page..."
  open "https://www.python.org/downloads/macos/" >/dev/null 2>&1
  echo "Install a newer Python, then run Start-Mac.command again."
else
  python3 App/app.py "$@"
fi
printf '\nPress Return to close this window. '
read -r answer
