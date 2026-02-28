#!/usr/bin/env bash
# Deploy application to the SoftLanding server
#
# Builds Docker images (ARM), pushes to GHCR, then pulls on server.
# All services run in Docker — no host installs needed.
#
# Usage:
#   bash infra/deploy.sh              # Deploy all
#   bash infra/deploy.sh backend      # Deploy backend only
#   bash infra/deploy.sh dashboard    # Deploy dashboard only
#   bash infra/deploy.sh docs         # Deploy documentation only
#   bash infra/deploy.sh landing      # Deploy landing page only
#   bash infra/deploy.sh caddy        # Deploy Caddyfile only

set -euo pipefail

COMPONENT="${1:-all}"
BACKEND_IMAGE="ghcr.io/sussdorff/soft-landing-backend"
DASHBOARD_IMAGE="ghcr.io/sussdorff/soft-landing-dashboard"
DOCS_IMAGE="ghcr.io/sussdorff/soft-landing-docs"
LANDING_IMAGE="ghcr.io/sussdorff/soft-landing-landing"
SHA=$(git rev-parse --short HEAD)

deploy_backend() {
  echo "==> Building backend image (linux/arm64)"
  docker buildx build --platform linux/arm64 \
    -t "${BACKEND_IMAGE}:${SHA}" \
    -t "${BACKEND_IMAGE}:latest" \
    --push backend/
  echo "    Image pushed: ${BACKEND_IMAGE}:${SHA}"

  echo "==> Pulling on server"
  ssh softlanding "cd /opt/softlanding && docker compose pull backend && docker compose up -d backend"
  echo "    Backend deployed"
}

deploy_dashboard() {
  echo "==> Building dashboard image (linux/arm64)"
  docker buildx build --platform linux/arm64 \
    -t "${DASHBOARD_IMAGE}:${SHA}" \
    -t "${DASHBOARD_IMAGE}:latest" \
    --push dashboard/
  echo "    Image pushed: ${DASHBOARD_IMAGE}:${SHA}"

  echo "==> Pulling on server"
  ssh softlanding "cd /opt/softlanding && docker compose pull dashboard && docker compose up -d dashboard"
  echo "    Dashboard deployed"
}

deploy_docs() {
  echo "==> Building docs image (linux/arm64)"
  docker buildx build --platform linux/arm64 \
    -t "${DOCS_IMAGE}:${SHA}" \
    -t "${DOCS_IMAGE}:latest" \
    --push docs/
  echo "    Image pushed: ${DOCS_IMAGE}:${SHA}"

  echo "==> Pulling on server"
  ssh softlanding "cd /opt/softlanding && docker compose pull docs && docker compose up -d docs"
  echo "    Docs deployed"
}

deploy_landing() {
  echo "==> Building landing image (linux/arm64)"
  docker buildx build --platform linux/arm64 \
    -t "${LANDING_IMAGE}:${SHA}" \
    -t "${LANDING_IMAGE}:latest" \
    --push landing/
  echo "    Image pushed: ${LANDING_IMAGE}:${SHA}"

  echo "==> Pulling on server"
  ssh softlanding "cd /opt/softlanding && docker compose pull landing && docker compose up -d landing"
  echo "    Landing deployed"
}

deploy_compose() {
  echo "==> Deploying docker-compose.yml + Caddyfile to server"
  scp docker-compose.prod.yml softlanding:/opt/softlanding/docker-compose.yml
  scp infra/Caddyfile softlanding:/opt/softlanding/Caddyfile
}

deploy_caddy() {
  echo "==> Deploying Caddyfile to server"
  scp infra/Caddyfile softlanding:/opt/softlanding/Caddyfile
  ssh softlanding "cd /opt/softlanding && docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile"
  echo "    Caddy reloaded"
}

case "${COMPONENT}" in
  all)
    deploy_compose
    deploy_backend
    deploy_dashboard
    deploy_docs
    deploy_landing
    ;;
  backend)   deploy_backend ;;
  dashboard) deploy_dashboard ;;
  compose)   deploy_compose ;;
  docs)      deploy_docs ;;
  landing)   deploy_landing ;;
  caddy)     deploy_caddy ;;
  *)
    echo "Unknown component: ${COMPONENT}"
    echo "Usage: $0 [all|backend|dashboard|compose|docs|landing|caddy]"
    exit 1
    ;;
esac

echo ""
echo "=== Deploy Complete ==="
echo "https://softlanding.sussdorff.de"
