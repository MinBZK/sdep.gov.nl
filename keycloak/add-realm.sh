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

echo "📦 Creating ${KEYCLOAK_REALM} realm in Keycloak..."
echo "🔐 Authenticating with Keycloak admin..."

TOKEN_RESPONSE=$(curl -s -X POST "${KEYCLOAK_BASE_URL}/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${KC_BOOTSTRAP_ADMIN_USERNAME}" \
    -d "password=${KC_BOOTSTRAP_ADMIN_PASSWORD}" \
    -d "grant_type=password" \
    -d "client_id=admin-cli")

TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to authenticate with Keycloak admin"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Authentication successful"
echo "🔍 Checking if ${KEYCLOAK_REALM} realm already exists..."

REALM_EXISTS=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}" \
    -o /dev/null -w "%{http_code}")

if [ "$REALM_EXISTS" = "200" ]; then
    echo "✅ Realm ${KEYCLOAK_REALM} already exists, skipping creation"
else
    echo "📝 Creating realm ${KEYCLOAK_REALM}..."
    RESPONSE=$(curl -s -X POST "${KEYCLOAK_BASE_URL}/admin/realms" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"realm\":\"${KEYCLOAK_REALM}\",\"enabled\":true,\"displayName\":\"SDEP Application\"}" \
        -w "%{http_code}")

    if echo "$RESPONSE" | grep -q "201"; then
        echo "✅ Realm ${KEYCLOAK_REALM} created successfully"
    else
        echo "❌ Failed to create realm ${KEYCLOAK_REALM}"
        echo "Response: $RESPONSE"
        exit 1
    fi
fi

echo "✅ Realm setup completed"
