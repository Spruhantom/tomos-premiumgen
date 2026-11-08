#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="tomos-premiumgen"
INSTALL_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/${APP_NAME}"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
VENV="${INSTALL_DIR}/venv"
REPO_URL="https://github.com/Spruhantom/tomos-premiumgen/archive/refs/heads/main.tar.gz"

log() { printf '[%s] %s\n' "$APP_NAME" "$*"; }
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }

if [[ "${1:-}" == "--uninstall" ]]; then
  rm -rf "$INSTALL_DIR"
  rm -f "$BIN_DIR/tomos-premiumgen" "$BIN_DIR/tomos-premiumgen-tui" "$BIN_DIR/tomos-premiumgen-gui"
  rm -f "$DESKTOP_DIR/tomos-premiumgen.desktop"
  log "Application removed. System GTK/Python packages and signing keys were left untouched."
  exit 0
fi
[[ $# -eq 0 ]] || die "Usage: install.sh [--uninstall]"

command -v curl >/dev/null 2>&1 || die "curl is required."
command -v python3 >/dev/null 2>&1 || die "Python 3.10 or newer is required."
python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 or newer is required.")
PY

[[ -r /etc/os-release ]] || die "Cannot identify this Linux distribution."
# shellcheck disable=SC1091
source /etc/os-release
ID_LIKE="${ID_LIKE:-}"
DISTRO="${ID:-}"
if [[ "$DISTRO" == "debian" || "$DISTRO" == "ubuntu" || "$ID_LIKE" == *debian* ]]; then
  PM="apt-get"; GTK_PACKAGES=(python3-gi gir1.2-gtk-4.0); BASE_PACKAGES=(python3 python3-venv python3-pip curl)
elif [[ "$DISTRO" == "fedora" || "$ID_LIKE" == *fedora* || "$ID_LIKE" == *rhel* ]]; then
  PM="dnf"; GTK_PACKAGES=(python3-gobject gtk4); BASE_PACKAGES=(python3 python3-pip curl)
elif [[ "$DISTRO" == "arch" || "$ID_LIKE" == *arch* || "$DISTRO" == "manjaro" || "$DISTRO" == "omarchy" ]]; then
  PM="pacman"; GTK_PACKAGES=(python-gobject gtk4); BASE_PACKAGES=(python python-pip curl)
else
  die "Unsupported distribution: $DISTRO. Supported: Debian, Ubuntu, Fedora and Arch Linux."
fi

if ! command -v sudo >/dev/null 2>&1 && [[ $EUID -ne 0 ]]; then
  die "sudo is required once to install GTK 4 system dependencies."
fi
as_root() { if [[ $EUID -eq 0 ]]; then "$@"; else sudo "$@"; fi; }

log "Installing GTK 4 runtime and Python bindings using $PM."
case "$PM" in
  apt-get) as_root apt-get update; as_root apt-get install -y "${BASE_PACKAGES[@]}" "${GTK_PACKAGES[@]}" ;;
  dnf) as_root dnf install -y "${BASE_PACKAGES[@]}" "${GTK_PACKAGES[@]}" ;;
  pacman) as_root pacman -S --needed --noconfirm "${BASE_PACKAGES[@]}" "${GTK_PACKAGES[@]}" ;;
esac

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
log "Downloading application source."
curl -fsSL "$REPO_URL" -o "$TMP_DIR/source.tar.gz"
tar -xzf "$TMP_DIR/source.tar.gz" -C "$TMP_DIR"
SOURCE_DIR="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n1)"
[[ -n "$SOURCE_DIR" ]] || die "Downloaded source archive is empty."

# Recreate an older venv if it cannot see the host's distro-provided GTK bindings.
if [[ -x "$VENV/bin/python" ]] && ! grep -q '^include-system-site-packages = true' "$VENV/pyvenv.cfg"; then
  rm -rf "$VENV"
fi
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv --system-site-packages "$VENV"
fi
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install --upgrade "$SOURCE_DIR"
ln -sfn "$VENV/bin/tomos-premiumgen" "$BIN_DIR/tomos-premiumgen"
ln -sfn "$VENV/bin/tomos-premiumgen-tui" "$BIN_DIR/tomos-premiumgen-tui"
ln -sfn "$VENV/bin/tomos-premiumgen-gui" "$BIN_DIR/tomos-premiumgen-gui"

cat > "$DESKTOP_DIR/tomos-premiumgen.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=TomOS Premium Code Generator
Comment=Generate and verify TomOS SIP Premium lifetime licences
Exec=$BIN_DIR/tomos-premiumgen-gui
Terminal=false
Categories=Utility;Development;
StartupNotify=true
EOF
chmod 644 "$DESKTOP_DIR/tomos-premiumgen.desktop"

log "Installation complete."
log "Launch from your desktop application menu or run: $BIN_DIR/tomos-premiumgen-gui"
log "CLI remains available as: $BIN_DIR/tomos-premiumgen"
log "Uninstall with: curl -fsSL https://raw.githubusercontent.com/Spruhantom/tomos-premiumgen/main/install.sh | bash -s -- --uninstall"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then log "Add $BIN_DIR to PATH to use the commands directly."; fi
