#!/bin/sh
cd "$(dirname "$0")" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ is required. Install it from https://www.python.org/downloads/macos/"
else
  python3 App/app.py "$@"
fi
printf '\nPress Return to close this window. '
read -r answer
