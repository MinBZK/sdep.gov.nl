#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

# Load environment variables if .env exists
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

echo "⏳ Waiting for Keycloak to be ready..."

# First wait for HTTP endpoint
until curl -sf "${KEYCLOAK_BASE_URL}" > /dev/null 2>&1; do
    printf "."
    sleep 2
done

# Then wait for admin API to be ready by checking the master realm endpoint
until curl -sf "${KEYCLOAK_BASE_URL}/realms/master/.well-known/openid-configuration" > /dev/null 2>&1; do
    printf "."
    sleep 2
done

# Finally, verify we can authenticate
MAX_RETRIES=10
RETRY_COUNT=0
until [ $RETRY_COUNT -ge $MAX_RETRIES ]; do
    TOKEN_RESPONSE=$(curl -sf -X POST "${KEYCLOAK_BASE_URL}/realms/master/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=${KC_BOOTSTRAP_ADMIN_USERNAME}" \
        -d "password=${KC_BOOTSTRAP_ADMIN_PASSWORD}" \
        -d "grant_type=password" \
        -d "client_id=admin-cli" 2>&1 || echo "")

    if echo "$TOKEN_RESPONSE" | grep -q "access_token"; then
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        printf "."
        sleep 2
    fi
done

if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo ""
    echo "❌ Failed to authenticate with Keycloak after $MAX_RETRIES retries"
    exit 1
fi

echo ""
echo "✅ Keycloak is ready!"
