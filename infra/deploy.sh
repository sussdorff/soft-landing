#!/usr/bin/env bash
# Deploy application to the SoftLanding server
#
# Builds Docker images (ARM), pushes to GHCR, then pulls on server.
# Docs and landing page are still rsync-deployed (simple static files).
#
# Usage:
#   bash infra/deploy.sh              # Deploy all
#   bash infra/deploy.sh backend      # Deploy backend only
#   bash infra/deploy.sh dashboard    # Deploy dashboard only
#   bash infra/deploy.sh docs         # Deploy documentation only
#   bash infra/deploy.sh landing      # Deploy landing page only

set -euo pipefail

COMPONENT="${1:-all}"
BACKEND_IMAGE="ghcr.io/sussdorff/soft-landing-backend"
DASHBOARD_IMAGE="ghcr.io/sussdorff/soft-landing-dashboard"
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

deploy_compose() {
  echo "==> Deploying docker-compose.yml to server"
  scp docker-compose.prod.yml softlanding:/opt/softlanding/docker-compose.yml
}

deploy_docs() {
  echo "==> Deploying docs"
  (cd docs && pip install -r requirements.txt -q && mkdocs build)
  rsync -avz --delete docs/site/ "softlanding:/opt/softlanding/docs/site/"
  echo "    Docs deployed"
}

deploy_landing() {
  echo "==> Deploying landing page"
  rsync -avz --delete \
    landing/ "softlanding:/opt/softlanding/landing/"
  echo "    Landing page deployed"
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
  *)
    echo "Unknown component: ${COMPONENT}"
    echo "Usage: $0 [all|backend|dashboard|compose|docs|landing]"
    exit 1
    ;;
esac

echo ""
echo "=== Deploy Complete ==="
echo "https://softlanding.sussdorff.de"
