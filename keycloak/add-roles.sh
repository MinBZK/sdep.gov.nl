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

echo "📦 Creating realm roles in ${KEYCLOAK_REALM}..."
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

# Create sdep_read role
echo "🔍 Creating sdep_read role..."
ROLE_EXISTS=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/roles/sdep_read" \
    -o /dev/null -w "%{http_code}")

if [ "$ROLE_EXISTS" = "200" ]; then
    echo "✅ Role sdep_read already exists, skipping creation"
else
    RESPONSE=$(curl -s -X POST "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/roles" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"name":"sdep_read","description":"Permission to read data"}' \
        -w "%{http_code}")

    if echo "$RESPONSE" | grep -q "201"; then
        echo "✅ Role sdep_read created successfully"
    else
        echo "❌ Failed to create role sdep_read"
        echo "Response: $RESPONSE"
        exit 1
    fi
fi

# Create sdep_write role
echo "🔍 Creating sdep_write role..."
ROLE_EXISTS=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/roles/sdep_write" \
    -o /dev/null -w "%{http_code}")

if [ "$ROLE_EXISTS" = "200" ]; then
    echo "✅ Role sdep_write already exists, skipping creation"
else
    RESPONSE=$(curl -s -X POST "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/roles" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"name":"sdep_write","description":"Permission to write data"}' \
        -w "%{http_code}")

    if echo "$RESPONSE" | grep -q "201"; then
        echo "✅ Role sdep_write created successfully"
    else
        echo "❌ Failed to create role sdep_write"
        echo "Response: $RESPONSE"
        exit 1
    fi
fi

# Create sdep_str role
echo "🔍 Creating sdep_str role..."
ROLE_EXISTS=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/roles/sdep_str" \
    -o /dev/null -w "%{http_code}")

if [ "$ROLE_EXISTS" = "200" ]; then
    echo "✅ Role sdep_str already exists, skipping creation"
else
    RESPONSE=$(curl -s -X POST "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/roles" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"name":"sdep_str","description":"Short-term rental (STR) platform role"}' \
        -w "%{http_code}")

    if echo "$RESPONSE" | grep -q "201"; then
        echo "✅ Role sdep_str created successfully"
    else
        echo "❌ Failed to create role sdep_str"
        echo "Response: $RESPONSE"
        exit 1
    fi
fi

# Create sdep_ca role
echo "🔍 Creating ca role..."
ROLE_EXISTS=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/roles/sdep_ca" \
    -o /dev/null -w "%{http_code}")

if [ "$ROLE_EXISTS" = "200" ]; then
    echo "✅ Role sdep_ca already exists, skipping creation"
else
    RESPONSE=$(curl -s -X POST "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/roles" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"name":"sdep_ca","description":"SDEP competent authority (CA) role"}' \
        -w "%{http_code}")

    if echo "$RESPONSE" | grep -q "201"; then
        echo "✅ Role sdep_ca created successfully"
    else
        echo "❌ Failed to create role sdep_ca"
        echo "Response: $RESPONSE"
        exit 1
    fi
fi

echo "✅ Realm roles setup completed"
