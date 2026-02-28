#!/usr/bin/env bash
# Provision the SoftLanding server
#
# Installs Docker and creates the app directory. All services (including
# Caddy reverse proxy) run inside docker-compose — no host installs needed.
#
# Usage: bash infra/provision.sh

set -euo pipefail

SERVER_NAME="softlanding"
SERVER_IP=$(hcloud server ip "${SERVER_NAME}")
DOMAIN="softlanding.sussdorff.de"

echo "==> Provisioning ${SERVER_NAME} (${SERVER_IP})"

ssh softlanding bash -s "${DOMAIN}" << 'REMOTE_SCRIPT'
set -euo pipefail

DOMAIN="$1"
export DEBIAN_FRONTEND=noninteractive

echo "==> Updating system"
apt-get update -qq
apt-get upgrade -y -qq

echo "==> Installing base packages"
apt-get install -y -qq \
  curl wget git unzip jq \
  ca-certificates gnupg

# --- Docker ---
echo "==> Installing Docker"
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi
docker --version

# --- Migrate from host Caddy to Docker Caddy ---
if systemctl is-active --quiet caddy 2>/dev/null; then
  echo "==> Stopping host Caddy (replaced by Docker Caddy)"
  systemctl stop caddy
  systemctl disable caddy
fi

# --- App directory ---
echo "==> Creating app directory"
mkdir -p /opt/softlanding

# --- Remove legacy standalone Postgres (replaced by docker-compose) ---
if docker ps -a --format '{{.Names}}' | grep -q softlanding-pg; then
  echo "==> Removing legacy standalone Postgres container"
  docker rm -f softlanding-pg 2>/dev/null || true
fi

echo "==> Provision complete"
echo "    Domain: https://${DOMAIN}"
echo "    Docker Compose: /opt/softlanding/docker-compose.yml"
REMOTE_SCRIPT

echo ""
echo "=== Provisioning Complete ==="
echo "Server:    ${SERVER_IP}"
echo "URL:       https://${DOMAIN}"
echo "API:       https://${DOMAIN}/api/"
echo "Dashboard: https://${DOMAIN}/dashboard/"
echo "Docs:      https://${DOMAIN}/docs/"
echo ""
echo "All services run inside Docker. Deploy with: bash infra/deploy.sh"
