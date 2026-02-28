#!/usr/bin/env bash
# Deploy application code to the SoftLanding server
#
# Syncs backend, dashboard, and passenger-app code to the server
# and restarts services as needed.
#
# Usage:
#   bash infra/deploy.sh              # Deploy all
#   bash infra/deploy.sh backend      # Deploy backend only
#   bash infra/deploy.sh dashboard    # Deploy dashboard only
#   bash infra/deploy.sh app          # Deploy passenger app only

set -euo pipefail

COMPONENT="${1:-all}"

deploy_backend() {
  echo "==> Deploying backend"
  rsync -avz --delete \
    --exclude '__pycache__' --exclude '.venv' --exclude '*.pyc' \
    backend/ "softlanding:/opt/softlanding/backend/"

  ssh softlanding bash << 'EOF'
cd /opt/softlanding/backend
if [ -f pyproject.toml ]; then
  /root/.local/bin/uv sync --python python3.14
  # Restart backend service if running
  systemctl restart softlanding-backend 2>/dev/null || true
fi
EOF
  echo "    Backend deployed"
}

deploy_dashboard() {
  echo "==> Deploying dashboard"
  # Build locally first if package.json exists
  if [ -f dashboard/package.json ]; then
    (cd dashboard && npm ci && npm run build)
  fi

  rsync -avz --delete \
    --exclude 'node_modules' --exclude '.next' \
    dashboard/ "softlanding:/opt/softlanding/dashboard/"
  echo "    Dashboard deployed"
}

deploy_app() {
  echo "==> Deploying passenger app (web target)"
  # KMP web build output — adjust path as needed
  rsync -avz --delete \
    passenger-app/ "softlanding:/opt/softlanding/passenger-app/"
  echo "    Passenger app deployed"
}

case "${COMPONENT}" in
  all)
    deploy_backend
    deploy_dashboard
    deploy_app
    ;;
  backend)  deploy_backend ;;
  dashboard) deploy_dashboard ;;
  app)      deploy_app ;;
  *)
    echo "Unknown component: ${COMPONENT}"
    echo "Usage: $0 [all|backend|dashboard|app]"
    exit 1
    ;;
esac

echo ""
echo "=== Deploy Complete ==="
echo "https://softlanding.sussdorff.de"
