#!/usr/bin/env bash
# Get a fresh OAuth2 token from the Lufthansa Open API.
# Usage: TOKEN=$(bash get-token.sh [client_id] [client_secret])
#
# Falls back to env vars LH_API_CLIENT_ID / LH_API_CLIENT_SECRET
# or the hardcoded hackathon credentials.

set -euo pipefail

CLIENT_ID="${1:-${LH_API_CLIENT_ID:-u4bnhm9uhcmq5yjt588sarh7}}"
CLIENT_SECRET="${2:-${LH_API_CLIENT_SECRET:-TYCf4nYDvfwc9StPyBnk}}"

/usr/bin/curl -s -X POST "https://api.lufthansa.com/v1/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${CLIENT_ID}&client_secret=${CLIENT_SECRET}&grant_type=client_credentials" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])"
