# Debian home-server deployment

This guide deploys the TomOS Premium redemption API on a Debian server as a
systemd service, with Caddy providing public HTTPS.

> **Status:** the installer and CI checks are in the repository, but a real
> installation on your own Debian host is still required before relying on the
> service commercially. The API does not currently provide customer
> authentication, payment processing, remote revocation or distributed rate
> limiting.

## Requirements

- A supported, up-to-date Debian system with sudo/root access.
- A stable, globally routable public IPv4 address.
- Router access to forward inbound TCP ports 80 and 443 to the Debian host.
- A working DNS-free route to the IP address and outbound internet access.
- An administrator-controlled signing keypair. Keep the private key off the
  server and out of this repository.

If your router's WAN address is not the public address, or your ISP uses
carrier-grade NAT (CGNAT), inbound port forwarding will not work. Ask your ISP
for a public IPv4 address or use a separately designed tunnel/reverse-proxy
architecture.

## Install

Replace the example IP and email with your real public IPv4 address and a
working ACME contact email:

```bash
curl -fsSL https://raw.githubusercontent.com/Spruhantom/tomos-premiumgen/main/install.sh | sudo bash -s -- --install-server --public-ip 203.0.113.10 --email admin@example.com
```

The installer is Debian-only. It installs the Python runtime and application
dependencies, Caddy, and a dedicated unprivileged `tomospremium` service
account. The API binds to `127.0.0.1:8000`; Caddy is the public HTTPS endpoint.
The SQLite database is stored at
`/var/lib/tomos-premiumgen/licences.sqlite3`.

The Caddy configuration requests a Let's Encrypt IP-address certificate using
the `shortlived` ACME profile. These certificates have a 160-hour lifetime;
Caddy must remain enabled, running and able to reach the ACME service to renew
them. A changed public IP requires rerunning the installer with the new IP.

## Network and firewall

1. Give the Debian host a reserved LAN address in your router.
2. Forward external TCP 80 to the host's TCP 80.
3. Forward external TCP 443 to the host's TCP 443.
4. Allow TCP 80 and 443 through the host firewall.
5. Confirm the router WAN IPv4 matches the IP supplied to the installer.

Do not forward port 8000. It is intentionally loopback-only.

## Verify the deployment

On the Debian host:

```bash
sudo systemctl status tomos-premiumgen-server
sudo systemctl status caddy
sudo journalctl -u tomos-premiumgen-server -n 100 --no-pager
sudo journalctl -u caddy -n 100 --no-pager
curl -fsS http://127.0.0.1:8000/health
```

From a device outside your home network, test:

```bash
curl -fsS https://YOUR_PUBLIC_IPV4/health
```

A successful health response confirms the API is reachable through the HTTPS
proxy. It does not by itself prove the complete purchase, activation or Android
signature-verification workflow.

## Import licences

Create and sign licence documents on the trusted administrator machine. Copy
only the required public key and individual licence document to the server
through a secure channel, or use a controlled local import process. The
`tomospremium` service account must be able to read those two files.

Example import (replace paths and activation code):

```bash
sudo -u tomospremium /opt/tomos-premiumgen-server/venv/bin/tomos-premiumgen register \
  --public-key /secure/import/public.pem \
  --licence /secure/import/customer.json \
  --activation-code 'CUSTOMER-ACTIVATION-CODE' \
  --database /var/lib/tomos-premiumgen/licences.sqlite3
```

Do not put activation codes in shell history, tickets, chat messages or public
logs. Restrict and remove temporary import files after use.

## Backups

The database contains licence redemption state and must be backed up securely.
For a consistent SQLite backup, use SQLite's backup facility while the service
is running, or stop the API briefly before copying the database:

```bash
sudo systemctl stop tomos-premiumgen-server
sudo install -d -m 700 /root/tomos-premium-backups
sudo cp -a /var/lib/tomos-premiumgen/licences.sqlite3 /root/tomos-premium-backups/
sudo systemctl start tomos-premiumgen-server
```

Encrypt off-host backups and periodically test restoring them. The uninstall
command intentionally retains the database.

## Service operations

```bash
sudo systemctl restart tomos-premiumgen-server
sudo systemctl stop tomos-premiumgen-server
sudo systemctl start tomos-premiumgen-server
sudo systemctl enable tomos-premiumgen-server
sudo systemctl is-enabled tomos-premiumgen-server
```

To remove the server components while retaining licence data:

```bash
curl -fsSL https://raw.githubusercontent.com/Spruhantom/tomos-premiumgen/main/install.sh | sudo bash -s -- --uninstall-server
```

## Security and production readiness

- Keep the Ed25519 private signing key on the administrator workstation. The
  Android client should contain only the public verification key.
- The API is loopback-bound and Caddy blocks unused admin/import and API-doc
  routes. Do not expose port 8000.
- The current API does not authenticate customers or provide distributed rate
  limiting. HTTPS alone does not provide those controls.
- Add monitoring, tested backups, abuse controls, support procedures, and
  device-transfer/refund policies before commercial public launch.
- Do not assume a home-hosted service has production availability. Power,
  router, ISP and dynamic-address outages can interrupt redemption.

See [SECURITY.md](../SECURITY.md) and [REDEMPTION_API.md](REDEMPTION_API.md)
for the signing-key model and API behavior.
