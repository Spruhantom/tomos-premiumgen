#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="tomos-premiumgen"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/${APP_NAME}"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
VENV="${INSTALL_DIR}/venv"
PACKAGE_URL="https://github.com/Spruhantom/tomos-premiumgen/archive/refs/heads/main.tar.gz"

if ! command -v curl >/dev/null 2>&1; then
  printf 'Error: curl is required. Install it with your system package manager first.\n' >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  printf 'Error: Python 3.10 or newer is required.\n' >&2
  exit 1
fi
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Error: Python 3.10 or newer is required.")
PY

mkdir -p "$INSTALL_DIR" "$BIN_DIR"
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install --upgrade "$PACKAGE_URL"
ln -sfn "$VENV/bin/tomos-premiumgen" "$BIN_DIR/tomos-premiumgen"
ln -sfn "$VENV/bin/tomos-premiumgen-tui" "$BIN_DIR/tomos-premiumgen-tui"

printf '\nTomOS Premium Generator installed successfully.\n'
printf 'Run: tomos-premiumgen tui\n'
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  printf 'Add this to your shell profile if the command is not found:\n'
  printf '  export PATH="%s:$PATH"\n' "$BIN_DIR"
fi
