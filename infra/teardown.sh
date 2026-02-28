#!/usr/bin/env bash
# Teardown SoftLanding infrastructure
# Removes server, firewall, and DNS record
#
# Usage: bash infra/teardown.sh

set -euo pipefail

SERVER_NAME="softlanding"
FIREWALL_NAME="softlanding-fw"
DNS_ZONE_ID="817812"
DNS_RECORD_NAME="softlanding"

echo "==> This will destroy the SoftLanding server and all data on it."
read -rp "Are you sure? (yes/no): " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

# Get server IP before deletion for DNS cleanup
SERVER_IP=$(hcloud server ip "${SERVER_NAME}" 2>/dev/null || echo "")

# Delete server
echo "==> Deleting server: ${SERVER_NAME}"
if hcloud server describe "${SERVER_NAME}" &>/dev/null; then
  hcloud server delete "${SERVER_NAME}"
  echo "    Server deleted"
else
  echo "    Server not found, skipping"
fi

# Delete firewall
echo "==> Deleting firewall: ${FIREWALL_NAME}"
if hcloud firewall describe "${FIREWALL_NAME}" &>/dev/null; then
  hcloud firewall delete "${FIREWALL_NAME}"
  echo "    Firewall deleted"
else
  echo "    Firewall not found, skipping"
fi

# Remove DNS record
if [ -n "${SERVER_IP}" ]; then
  echo "==> Removing DNS: ${DNS_RECORD_NAME}.sussdorff.de"
  hcloud zone remove-records --record "${SERVER_IP}" "${DNS_ZONE_ID}" "${DNS_RECORD_NAME}" A 2>/dev/null || true
  echo "    DNS record removed"
fi

echo ""
echo "=== Teardown Complete ==="
