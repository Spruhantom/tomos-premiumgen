#!/usr/bin/env bash
# Install the TomOS Premium redemption API as a hardened system service on Debian.
set -Eeuo pipefail

APP="tomos-premiumgen"
SERVICE_USER="tomospremium"
APP_DIR="/opt/tomos-premiumgen-server"
STATE_DIR="/var/lib/tomos-premiumgen"
CONFIG_DIR="/etc/tomos-premiumgen"
UNIT="/etc/systemd/system/tomos-premiumgen-server.service"
CADDYFILE="/etc/caddy/Caddyfile"
REPO_ARCHIVE="https://github.com/Spruhantom/tomos-premiumgen/archive/refs/heads/main.tar.gz"
PUBLIC_IP=""
ACME_EMAIL=""
UNINSTALL=0

log() { printf '[%s-server] %s\n' "$APP" "$*"; }
die() { printf 'Error: %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'USAGE'
Usage:
  server-install.sh --public-ip <public-ipv4> --email <acme-email>
  server-install.sh --uninstall

Installs the API as a systemd daemon behind Caddy HTTPS using a short-lived
Let's Encrypt IP-address certificate. Run as root on Debian 12 or newer.
The router must forward TCP ports 80 and 443 to this server.
USAGE
}

while (($#)); do
  case "$1" in
    --public-ip) (($# >= 2)) || die "--public-ip requires an IPv4 address"; PUBLIC_IP="$2"; shift 2 ;;
    --email) (($# >= 2)) || die "--email requires an address"; ACME_EMAIL="$2"; shift 2 ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage; die "Unknown option: $1" ;;
  esac
done

[[ $EUID -eq 0 ]] || die "Run with sudo or as root."
[[ -r /etc/os-release ]] || die "Cannot identify operating system."
. /etc/os-release
[[ "${ID:-}" == "debian" ]] || die "This server installer currently supports Debian only."
if [[ "$UNINSTALL" -eq 1 ]]; then
  systemctl disable --now tomos-premiumgen-server.service 2>/dev/null || true
  rm -f "$UNIT"
  systemctl daemon-reload
  if [[ -f "${CADDYFILE}.pre-tomos-premiumgen" ]]; then
    cp -a "${CADDYFILE}.pre-tomos-premiumgen" "$CADDYFILE"
    rm -f "${CADDYFILE}.pre-tomos-premiumgen"
    systemctl restart caddy 2>/dev/null || true
  elif [[ -f "$CADDYFILE" ]] && grep -qF "# BEGIN TOMOS PREMIUM API" "$CADDYFILE"; then
    rm -f "$CADDYFILE"
    systemctl stop caddy 2>/dev/null || true
  fi
  rm -rf "$APP_DIR" "$CONFIG_DIR"
  log "Service and application files removed. Licence database retained at $STATE_DIR."
  log "Caddy was left installed. Review /etc/caddy/Caddyfile before restarting it."
  exit 0
fi

[[ -n "$PUBLIC_IP" && -n "$ACME_EMAIL" ]] || { usage; die "Both --public-ip and --email are required."; }
python3 - "$PUBLIC_IP" "$ACME_EMAIL" <<'PY'
import ipaddress, re, sys
try:
    ip = ipaddress.ip_address(sys.argv[1])
except ValueError:
    raise SystemExit("A valid public IPv4 address is required.")
if ip.version != 4 or not ip.is_global:
    raise SystemExit("The address must be a globally routable public IPv4 address.")
if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", sys.argv[2]):
    raise SystemExit("A valid ACME contact email address is required.")
PY
[[ -f /etc/debian_version ]] || die "Debian release information is missing."

log "Installing Python, build tools and Caddy prerequisites."
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg python3 python3-venv python3-pip

# Install Caddy from its official Debian repository.
install -d -m 0755 /usr/share/keyrings
curl -fsSL 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
chmod 0644 /usr/share/keyrings/caddy-stable-archive-keyring.gpg
printf '%s\n' 'deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/deb/debian any-version main' > /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get install -y caddy

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home-dir /nonexistent --shell /usr/sbin/nologin "$SERVICE_USER"
fi
install -d -o root -g root -m 0755 "$APP_DIR"
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0700 "$STATE_DIR"
install -d -o root -g "$SERVICE_USER" -m 0750 "$CONFIG_DIR"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
log "Downloading the TomOS Premium server source."
curl -fsSL "$REPO_ARCHIVE" -o "$TMP_DIR/source.tar.gz"
tar -xzf "$TMP_DIR/source.tar.gz" -C "$TMP_DIR"
SOURCE_DIR="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | head -n1)"
[[ -n "$SOURCE_DIR" ]] || die "The source archive was empty."
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/python" -m pip install --no-cache-dir --upgrade pip
"$APP_DIR/venv/bin/python" -m pip install --no-cache-dir "$SOURCE_DIR[server]"
chown -R root:root "$APP_DIR"
chmod -R go-w "$APP_DIR"

# Never overwrite an administrator-managed unit or Caddy configuration.
if [[ -e "$UNIT" ]]; then die "$UNIT already exists; refusing to overwrite it."; fi
if [[ -e "$CADDYFILE" ]]; then
  cp -a "$CADDYFILE" "${CADDYFILE}.pre-tomos-premiumgen"
  if grep -qF "# BEGIN TOMOS PREMIUM API" "$CADDYFILE"; then
    die "A TomOS Premium Caddy block already exists. Inspect $CADDYFILE before retrying."
  fi
  CADDY_EXISTING="$(cat "$CADDYFILE")"
else
  CADDY_EXISTING=""
fi

cat > "$UNIT" <<UNIT
[Unit]
Description=TomOS Premium licence redemption API
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
Environment=TOMOS_LICENCE_DB=$STATE_DIR/licences.sqlite3
Environment=TOMOS_SERVER_HOST=127.0.0.1
Environment=TOMOS_SERVER_PORT=8000
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/tomos-premiumgen-server --host 127.0.0.1 --port 8000 --log-level info
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$STATE_DIR
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
LockPersonality=true
RestrictSUIDSGID=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6

[Install]
WantedBy=multi-user.target
UNIT
chmod 0644 "$UNIT"

{
  if [[ -n "$CADDY_EXISTING" ]]; then printf '%s\n' "$CADDY_EXISTING"; fi
  cat <<CADDY
# BEGIN TOMOS PREMIUM API
$PUBLIC_IP {
    tls {
        issuer acme {
            profile shortlived
        }
    }

    encode zstd gzip
    request_body {
        max_size 16KB
    }

    @blocked path /admin/* /docs* /redoc* /openapi.json
    respond @blocked 404

    reverse_proxy 127.0.0.1:8000
}
# END TOMOS PREMIUM API
CADDY
} > "$CADDYFILE"
chown root:caddy "$CADDYFILE"
chmod 0640 "$CADDYFILE"

log "Validating Caddy configuration."
caddy validate --config "$CADDYFILE" --adapter caddyfile
systemctl daemon-reload
systemctl enable --now tomos-premiumgen-server.service
systemctl enable caddy
systemctl restart caddy

log "Checking the local API health endpoint."
for attempt in {1..20}; do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null; then break; fi
  if [[ "$attempt" -eq 20 ]]; then
    journalctl -u tomos-premiumgen-server.service -n 50 --no-pager >&2 || true
    die "The API did not become healthy. See the service journal."
  fi
  sleep 1
done

log "TomOS Premium API service installed and running."
log "Local health: http://127.0.0.1:8000/health"
log "Public endpoint: https://$PUBLIC_IP"
log "Caddy will automatically renew the short-lived IP certificate (160-hour validity)."
log "Import licences locally with the tomos-premiumgen register command and this database: $STATE_DIR/licences.sqlite3"
log "Service status: systemctl status tomos-premiumgen-server"
log "Logs: journalctl -u tomos-premiumgen-server -f"
log "IMPORTANT: Forward router TCP ports 80 and 443 to this Debian server and allow them through your firewall."
log "IMPORTANT: Confirm the router WAN IPv4 matches $PUBLIC_IP; CGNAT or a changing IP prevents reliable direct hosting."
log "IMPORTANT: This API has no built-in distributed rate limiter or customer authentication; use firewall protections and monitor logs before commercial public launch."
