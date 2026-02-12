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
until curl -sf "${KC_BASE_URL}" > /dev/null 2>&1; do
    printf "."
    sleep 2
done

# Then wait for admin API to be ready by checking the master realm endpoint
until curl -sf "${KC_BASE_URL}/realms/master/.well-known/openid-configuration" > /dev/null 2>&1; do
    printf "."
    sleep 2
done

# Finally, verify we can authenticate
MAX_RETRIES=10
RETRY_COUNT=0
until [ $RETRY_COUNT -ge $MAX_RETRIES ]; do
    TOKEN_RESPONSE=$(curl -sf -X POST "${KC_BASE_URL}/realms/master/protocol/openid-connect/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=${KC_ADMIN_REALM_ADMIN_USERNAME}" \
        -d "password=${KC_ADMIN_REALM_ADMIN_PASSWORD}" \
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
    echo "" >&2
    echo "❌ Failed to authenticate with Keycloak after $MAX_RETRIES retries" >&2
    echo "" >&2
    echo "Configuration used:" >&2
    echo "  KC_BASE_URL: ${KC_BASE_URL}" >&2
    echo "  KC_ADMIN_REALM_ADMIN_USERNAME: ${KC_ADMIN_REALM_ADMIN_USERNAME}" >&2
    echo "  KC_ADMIN_REALM_ADMIN_PASSWORD: (${#KC_ADMIN_REALM_ADMIN_PASSWORD} characters)" >&2
    echo "" >&2
    echo "💡 Suggestion: KC_ADMIN_REALM_ADMIN_USERNAME and KC_ADMIN_REALM_ADMIN_PASSWORD should be" >&2
    echo "   the username and password of a Keycloak admin user in the master realm." >&2
    exit 1
fi

echo "✅ Keycloak is ready!"
