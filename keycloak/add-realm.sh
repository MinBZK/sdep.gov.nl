#!/usr/bin/env bash
set -euo pipefail

# Check required variables
if [ -z "${KC_BASE_URL:-}" ]; then
    echo "❌ Error: KC_BASE_URL is not set"
    exit 1
fi

if [ -z "${KC_APP_REALM:-}" ]; then
    echo "❌ Error: REALM is not set"
    exit 1
fi

if [ -z "${KC_ADMIN_REALM_ADMIN_USERNAME:-}" ]; then
    echo "❌ Error: KC_ADMIN_REALM_ADMIN_USERNAME is not set"
    exit 1
fi

if [ -z "${KC_ADMIN_REALM_ADMIN_PASSWORD:-}" ]; then
    echo "❌ Error: KC_ADMIN_REALM_ADMIN_PASSWORD is not set"
    exit 1
fi

if [ -z "${KC_APP_REALM_DISPLAYNAME:-}" ]; then
    echo "❌ Error: KC_APP_REALM_DISPLAYNAME is not set"
    exit 1
fi

echo "📦 Creating ${KC_APP_REALM} realm in Keycloak..."
echo "🔐 Authenticating with Keycloak admin..."

TOKEN_RESPONSE=$(curl -s -X POST "${KC_BASE_URL}/realms/master/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=${KC_ADMIN_REALM_ADMIN_USERNAME}" \
    -d "password=${KC_ADMIN_REALM_ADMIN_PASSWORD}" \
    -d "grant_type=password" \
    -d "client_id=admin-cli")

TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to authenticate with Keycloak admin"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Authentication successful"
echo "🔍 Checking if ${KC_APP_REALM} realm already exists..."

REALM_EXISTS=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}" \
    -o /dev/null -w "%{http_code}")

if [ "$REALM_EXISTS" = "200" ]; then
    echo "✅ Realm ${KC_APP_REALM} already exists, skipping creation"
else
    echo "📝 Creating realm ${KC_APP_REALM}..."
    RESPONSE=$(curl -s -X POST "${KC_BASE_URL}/admin/realms" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"realm\":\"${KC_APP_REALM}\",\"enabled\":true,\"displayName\":\"${KC_APP_REALM_DISPLAYNAME}\"}" \
        -w "%{http_code}")

    if echo "$RESPONSE" | grep -q "201"; then
        echo "✅ Realm ${KC_APP_REALM} created successfully"
    else
        echo "❌ Failed to create realm ${KC_APP_REALM}"
        echo "Response: $RESPONSE"
        exit 1
    fi
fi

echo "✅ Realm setup completed"
