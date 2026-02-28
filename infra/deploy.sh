#!/usr/bin/env bash
# Deploy application to the SoftLanding server
#
# Builds Docker images locally (cross-compile to ARM64), streams them
# to the server via SSH, and restarts services. No registry needed.
#
# Usage:
#   bash infra/deploy.sh                # Deploy all
#   bash infra/deploy.sh backend        # Deploy backend only
#   bash infra/deploy.sh dashboard      # Deploy dashboard only
#   bash infra/deploy.sh passenger-app  # Deploy passenger app only
#   bash infra/deploy.sh docs           # Deploy documentation only
#   bash infra/deploy.sh landing        # Deploy landing page only
#   bash infra/deploy.sh caddy          # Deploy Caddyfile only

set -euo pipefail

COMPONENT="${1:-all}"
SERVER="root@46.224.137.140"
REMOTE_DIR="/opt/softlanding"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

BACKEND_IMAGE="ghcr.io/sussdorff/soft-landing-backend:latest"
DASHBOARD_IMAGE="ghcr.io/sussdorff/soft-landing-dashboard:latest"
DOCS_IMAGE="ghcr.io/sussdorff/soft-landing-docs:latest"
LANDING_IMAGE="ghcr.io/sussdorff/soft-landing-landing:latest"
PASSENGER_APP_IMAGE="ghcr.io/sussdorff/soft-landing-passenger-app:latest"

build_and_push() {
  local context="$1"
  local image="$2"
  local name="$3"

  echo "==> Building ${name} (linux/arm64)"
  docker buildx build --platform linux/arm64 \
    -t "${image}" \
    --output type=docker,dest=- \
    "${context}" | ssh "${SERVER}" docker load
  echo "    ${name} image loaded on server"
}

deploy_backend() {
  build_and_push "${REPO_ROOT}/backend" "${BACKEND_IMAGE}" "backend"
  ssh "${SERVER}" "cd ${REMOTE_DIR} && docker compose up -d backend"
  echo "    Backend deployed"
}

deploy_dashboard() {
  build_and_push "${REPO_ROOT}/dashboard" "${DASHBOARD_IMAGE}" "dashboard"
  ssh "${SERVER}" "cd ${REMOTE_DIR} && docker compose up -d dashboard"
  echo "    Dashboard deployed"
}

deploy_docs() {
  build_and_push "${REPO_ROOT}/docs" "${DOCS_IMAGE}" "docs"
  ssh "${SERVER}" "cd ${REMOTE_DIR} && docker compose up -d docs"
  echo "    Docs deployed"
}

deploy_passenger_app() {
  echo "==> Building passenger app WASM (local Gradle build)"
  JAVA_HOME=/opt/homebrew/opt/openjdk/libexec/openjdk.jdk/Contents/Home \
    "${REPO_ROOT}/passenger-app/gradlew" -p "${REPO_ROOT}/passenger-app" \
    :composeApp:wasmJsBrowserDistribution --quiet
  echo "    WASM build complete"
  build_and_push "${REPO_ROOT}/passenger-app" "${PASSENGER_APP_IMAGE}" "passenger-app"
  ssh "${SERVER}" "cd ${REMOTE_DIR} && docker compose up -d passenger-app"
  echo "    Passenger app deployed"
}

deploy_landing() {
  build_and_push "${REPO_ROOT}/landing" "${LANDING_IMAGE}" "landing"
  ssh "${SERVER}" "cd ${REMOTE_DIR} && docker compose up -d landing"
  echo "    Landing deployed"
}

deploy_compose() {
  echo "==> Deploying docker-compose.yml to server"
  scp "${REPO_ROOT}/docker-compose.prod.yml" "${SERVER}:${REMOTE_DIR}/docker-compose.yml"
}

deploy_caddy() {
  echo "==> Deploying Caddyfile to server"
  scp "${REPO_ROOT}/infra/Caddyfile" "${SERVER}:${REMOTE_DIR}/Caddyfile"
  ssh "${SERVER}" "cd ${REMOTE_DIR} && docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile"
  echo "    Caddy reloaded"
}

case "${COMPONENT}" in
  all)
    deploy_compose
    deploy_backend
    deploy_dashboard
    deploy_passenger_app
    deploy_docs
    deploy_landing
    ;;
  backend)        deploy_compose; deploy_backend ;;
  dashboard)      deploy_compose; deploy_dashboard ;;
  passenger-app)  deploy_compose; deploy_passenger_app ;;
  docs)           deploy_compose; deploy_docs ;;
  landing)        deploy_compose; deploy_landing ;;
  compose)        deploy_compose ;;
  caddy)          deploy_caddy ;;
  *)
    echo "Unknown component: ${COMPONENT}"
    echo "Usage: $0 [all|backend|dashboard|passenger-app|compose|docs|landing|caddy]"
    exit 1
    ;;
esac

echo ""
echo "=== Deploy Complete ==="
echo "https://softlanding.sussdorff.de"
