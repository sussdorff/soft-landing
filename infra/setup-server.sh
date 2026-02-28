#!/usr/bin/env bash
# Infrastructure setup for SoftLanding / ReRoute
# Creates a Hetzner Cloud VPS with firewall and DNS record
#
# Prerequisites:
#   - hcloud CLI with 1Password shell plugin (Default project)
#   - SSH keys "Malte" and "Malte-ED25519" in Hetzner Cloud
#
# Usage: bash infra/setup-server.sh

set -euo pipefail

# --- Configuration ---
SERVER_NAME="softlanding"
SERVER_TYPE="cax11"          # ARM, 2 cores, 4GB RAM, 40GB disk (cheapest)
IMAGE="ubuntu-24.04"
LOCATION="fsn1"              # Falkenstein, DE
SSH_KEYS="Malte,Malte-ED25519"
FIREWALL_NAME="softlanding-fw"
DNS_ZONE_ID="817812"         # sussdorff.de
DNS_RECORD_NAME="softlanding"

# --- Firewall ---
echo "==> Creating firewall: ${FIREWALL_NAME}"
if hcloud firewall describe "${FIREWALL_NAME}" &>/dev/null; then
  echo "    Firewall already exists, skipping"
else
  hcloud firewall create --name "${FIREWALL_NAME}"

  # SSH
  hcloud firewall add-rule "${FIREWALL_NAME}" \
    --direction in --protocol tcp --port 22 \
    --source-ips 0.0.0.0/0 --source-ips ::/0 \
    --description "SSH"

  # HTTP
  hcloud firewall add-rule "${FIREWALL_NAME}" \
    --direction in --protocol tcp --port 80 \
    --source-ips 0.0.0.0/0 --source-ips ::/0 \
    --description "HTTP"

  # HTTPS
  hcloud firewall add-rule "${FIREWALL_NAME}" \
    --direction in --protocol tcp --port 443 \
    --source-ips 0.0.0.0/0 --source-ips ::/0 \
    --description "HTTPS"

  # WebSocket (same ports as HTTP/HTTPS, but also allow 8080 for dev)
  hcloud firewall add-rule "${FIREWALL_NAME}" \
    --direction in --protocol tcp --port 8080 \
    --source-ips 0.0.0.0/0 --source-ips ::/0 \
    --description "Dev/WebSocket alt port"

  echo "    Firewall created with SSH, HTTP, HTTPS, 8080 rules"
fi

# --- Server ---
echo "==> Creating server: ${SERVER_NAME}"
if hcloud server describe "${SERVER_NAME}" &>/dev/null; then
  echo "    Server already exists, skipping"
  SERVER_IP=$(hcloud server ip "${SERVER_NAME}")
else
  hcloud server create \
    --name "${SERVER_NAME}" \
    --type "${SERVER_TYPE}" \
    --image "${IMAGE}" \
    --location "${LOCATION}" \
    --ssh-key "${SSH_KEYS}" \
    --firewall "${FIREWALL_NAME}"

  SERVER_IP=$(hcloud server ip "${SERVER_NAME}")
  echo "    Server created: ${SERVER_IP}"

  # Wait for SSH to become available
  echo "==> Waiting for SSH..."
  for i in $(seq 1 30); do
    if ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=accept-new "root@${SERVER_IP}" true &>/dev/null; then
      echo "    SSH ready"
      break
    fi
    sleep 2
  done
fi

echo "    Server IP: ${SERVER_IP}"

# --- DNS ---
echo "==> Setting DNS: ${DNS_RECORD_NAME}.sussdorff.de -> ${SERVER_IP}"
hcloud zone set-records \
  --record "${SERVER_IP}" \
  "${DNS_ZONE_ID}" "${DNS_RECORD_NAME}" A

echo "    DNS record set"

# --- Summary ---
echo ""
echo "=== Setup Complete ==="
echo "Server:  ${SERVER_NAME} (${SERVER_TYPE}, ${LOCATION})"
echo "IP:      ${SERVER_IP}"
echo "DNS:     ${DNS_RECORD_NAME}.sussdorff.de -> ${SERVER_IP}"
echo "SSH:     ssh root@${SERVER_IP}"
echo ""
echo "Next: run 'bash infra/provision.sh' to install software"
