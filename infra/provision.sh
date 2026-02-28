#!/usr/bin/env bash
# Provision the SoftLanding server with required software
#
# Installs: Docker, Caddy (reverse proxy + TLS), Python 3.14, Node.js 22
# Sets up Caddy to reverse-proxy backend (Python) and serve static files
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
  build-essential pkg-config \
  libssl-dev libffi-dev \
  software-properties-common \
  apt-transport-https \
  ca-certificates gnupg

# --- Docker ---
echo "==> Installing Docker"
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi
docker --version

# --- Node.js 22 (for React dashboard build/serve) ---
echo "==> Installing Node.js 22"
if ! command -v node &>/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y -qq nodejs
fi
node --version
npm --version

# --- uv (Python package manager — also manages Python versions) ---
echo "==> Installing uv"
if ! command -v uv &>/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="/root/.local/bin:$PATH"
fi

# --- Python 3.14 via uv (works on ARM) ---
echo "==> Installing Python 3.14 via uv"
/root/.local/bin/uv python install 3.14
/root/.local/bin/uv python list --only-installed | grep 3.14

# --- Caddy (reverse proxy + automatic TLS) ---
echo "==> Installing Caddy"
if ! command -v caddy &>/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq
  apt-get install -y -qq caddy
fi
caddy version

# --- App directories ---
echo "==> Creating app directories"
mkdir -p /opt/softlanding/{docs/site,landing}

# --- Stop legacy standalone Postgres (replaced by docker-compose) ---
if docker ps -a --format '{{.Names}}' | grep -q softlanding-pg; then
  echo "==> Removing legacy standalone Postgres container"
  docker rm -f softlanding-pg 2>/dev/null || true
fi

# --- Caddyfile ---
echo "==> Writing Caddyfile"
cat > /etc/caddy/Caddyfile << CADDYFILE
${DOMAIN} {
    # CORS is handled by FastAPI middleware — do NOT add headers here
    # (duplicate Access-Control-Allow-Origin causes browsers to reject requests)

    # Redirect /docs to /docs/
    redir /docs /docs/ 308

    # User documentation (MkDocs Material)
    handle_path /docs/* {
        root * /opt/softlanding/docs/site
        file_server
    }

    # Redirect /dashboard to /dashboard/
    redir /dashboard /dashboard/ 308

    # Gate Agent Dashboard (nginx container)
    handle /dashboard/* {
        reverse_proxy localhost:3000
    }

    # Passenger App (KMP/Web target — static files)
    handle_path /app/* {
        root * /opt/softlanding/passenger-app/web
        try_files {path} /index.html
        file_server
    }

    # Backend API — everything else goes to FastAPI
    handle {
        reverse_proxy localhost:8000
    }
}

get-${DOMAIN} {
    root * /opt/softlanding/landing
    file_server
}
CADDYFILE

# Reload Caddy
systemctl enable caddy
systemctl restart caddy

echo "==> Provision complete"
echo "    Domain: https://${DOMAIN}"
echo "    Docker Compose: /opt/softlanding/docker-compose.yml"
echo "    Docs: /opt/softlanding/docs/site/"
REMOTE_SCRIPT

echo ""
echo "=== Provisioning Complete ==="
echo "Server:    ${SERVER_IP}"
echo "URL:       https://${DOMAIN}"
echo "API:       https://${DOMAIN}/api/"
echo "Dashboard: https://${DOMAIN}/dashboard/"
echo "App:       https://${DOMAIN}/app/"
echo ""
echo "Caddy handles TLS automatically via Let's Encrypt."
echo "CORS is enabled for mobile app access (Android/iOS KMP targets)."
