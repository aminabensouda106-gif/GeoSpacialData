#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

VENV=.venv-test
if [ ! -d "$VENV" ]; then
  python -m venv "$VENV"
fi

if [ -f "$VENV/Scripts/activate" ]; then
  # shellcheck disable=SC1091
  source "$VENV/Scripts/activate" # Windows venv layout
else
  # shellcheck disable=SC1091
  source "$VENV/bin/activate" # POSIX venv layout
fi

pip install -q -r tests/requirements.txt
pytest -q tests/
