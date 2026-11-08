#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALLER="$ROOT_DIR/install.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

assert_detection() {
  local id="$1" id_like="$2" manager="$3" gtk_packages="$4"
  local fixture="$TMP_DIR/os-release"
  printf 'ID=%s\nID_LIKE="%s"\nPRETTY_NAME="Test %s"\n' "$id" "$id_like" "$id" > "$fixture"
  local output
  output="$(TOMOS_OS_RELEASE_FILE="$fixture" bash "$INSTALLER" --check)"
  grep -Fq "package manager=$manager" <<< "$output"
  grep -Fq "GTK packages: $gtk_packages." <<< "$output"
  printf 'PASS: %s detected as %s\n' "$id" "$manager"
}

assert_detection debian "" apt-get "python3-gi gir1.2-gtk-4.0"
assert_detection ubuntu debian apt-get "python3-gi gir1.2-gtk-4.0"
assert_detection fedora "" dnf "python3-gobject gtk4"
assert_detection arch "" pacman "python-gobject gtk4"

fixture="$TMP_DIR/os-release"
printf 'ID=opensuse\nID_LIKE=""\n' > "$fixture"
if TOMOS_OS_RELEASE_FILE="$fixture" bash "$INSTALLER" --check >"$TMP_DIR/unsupported.out" 2>&1; then
  echo "Unsupported distribution was incorrectly accepted." >&2
  exit 1
fi
grep -Fq "Unsupported distribution: opensuse" "$TMP_DIR/unsupported.out"
echo "PASS: unsupported distribution rejected"
