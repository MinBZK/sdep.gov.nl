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

if [ -z "${KC_APP_REALM_ADMIN_USERNAME:-}" ]; then
    echo "❌ Error: KC_APP_REALM_ADMIN_USERNAME is not set"
    exit 1
fi

if [ -z "${KC_APP_REALM_ADMIN_PASSWORD:-}" ]; then
    echo "❌ Error: KC_APP_REALM_ADMIN_PASSWORD is not set"
    exit 1
fi

if [ -z "${KC_APP_REALM_ROLE_YAML:-}" ]; then
    echo "❌ Error: KC_APP_REALM_ROLE_YAML is not set"
    exit 1
fi

if [ ! -f "${KC_APP_REALM_ROLE_YAML}" ]; then
    echo "❌ Error: KC_APP_REALM_ROLE_YAML file not found: ${KC_APP_REALM_ROLE_YAML}"
    exit 1
fi

echo "📦 Creating realm roles in ${KC_APP_REALM} from ${KC_APP_REALM_ROLE_YAML}..."
echo "🔐 Authenticating with realm admin service account..."

TOKEN_RESPONSE=$(curl -s -X POST "${KC_BASE_URL}/realms/${KC_APP_REALM}/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=${KC_APP_REALM_ADMIN_USERNAME}" \
    -d "client_secret=${KC_APP_REALM_ADMIN_PASSWORD}" \
    -d "grant_type=client_credentials")

TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to authenticate with realm admin service account"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Authentication successful"
echo "📄 Managing roles in ${KC_APP_REALM} from ${KC_APP_REALM_ROLE_YAML}..."

# Get all existing roles in the realm
EXISTING_ROLES=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/roles")

# Build desired roles array from YAML and validate prefix
ROLE_COUNT=$(yq '.roles | length' "$KC_APP_REALM_ROLE_YAML")
REALM_PREFIX="${KC_APP_REALM}_"
DESIRED_ROLE_NAMES="["

for i in $(seq 0 $((ROLE_COUNT - 1))); do
    ROLE_NAME=$(yq ".roles[$i].name" "$KC_APP_REALM_ROLE_YAML")

    # Validate that role has REALM prefix
    if [[ ! "$ROLE_NAME" =~ ^${REALM_PREFIX} ]]; then
        echo "❌ Error: Role '$ROLE_NAME' does not have required prefix '${REALM_PREFIX}'"
        echo "All roles in YAML must start with '${REALM_PREFIX}'"
        exit 1
    fi

    if [ "$DESIRED_ROLE_NAMES" != "[" ]; then
        DESIRED_ROLE_NAMES="$DESIRED_ROLE_NAMES,"
    fi
    DESIRED_ROLE_NAMES="$DESIRED_ROLE_NAMES\"$ROLE_NAME\""
done
DESIRED_ROLE_NAMES="$DESIRED_ROLE_NAMES]"

# Process roles from YAML (create or update)
for i in $(seq 0 $((ROLE_COUNT - 1))); do
    ROLE_NAME=$(yq ".roles[$i].name" "$KC_APP_REALM_ROLE_YAML")
    ROLE_DESC=$(yq ".roles[$i].description" "$KC_APP_REALM_ROLE_YAML")

    ROLE_EXISTS=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/roles/$ROLE_NAME" \
        -o /dev/null -w "%{http_code}")

    if [ "$ROLE_EXISTS" = "200" ]; then
        echo "✅ Role $ROLE_NAME already exists"
    else
        echo "🔍 Creating role $ROLE_NAME..."
        ROLE_DATA=$(jq -n \
            --arg name "$ROLE_NAME" \
            --arg description "$ROLE_DESC" \
            '{name: $name, description: $description}')

        RESPONSE=$(curl -s -X POST "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/roles" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$ROLE_DATA" \
            -w "%{http_code}")

        if echo "$RESPONSE" | grep -q "201"; then
            echo "✅ Role $ROLE_NAME created successfully"
        else
            echo "❌ Failed to create role $ROLE_NAME"
            echo "Response: $RESPONSE"
            exit 1
        fi
    fi
done

# Remove roles that exist in realm but not in YAML (only those with REALM prefix)
echo "🔍 Checking for roles to remove..."
ROLES_TO_REMOVE=$(echo "$EXISTING_ROLES" | jq -r --argjson desired "$DESIRED_ROLE_NAMES" --arg prefix "${REALM_PREFIX}" \
    '[.[] | select(.composite == false and .clientRole == false and (.name | startswith($prefix)) and ([.name] | inside($desired) | not)) | .name] | .[]')

if [ -n "$ROLES_TO_REMOVE" ]; then
    while IFS= read -r ROLE_NAME; do
        echo "🗑️  Removing role $ROLE_NAME (not in YAML)..."
        DELETE_RESPONSE=$(curl -s -X DELETE "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/roles/$ROLE_NAME" \
            -H "Authorization: Bearer $TOKEN" \
            -w "%{http_code}")

        if [ "$DELETE_RESPONSE" = "204" ] || [ "$DELETE_RESPONSE" = "200" ]; then
            echo "✅ Role $ROLE_NAME removed successfully"
        else
            echo "❌ Failed to remove role $ROLE_NAME"
            echo "Response: $DELETE_RESPONSE"
            exit 1
        fi
    done <<< "$ROLES_TO_REMOVE"
else
    echo "✅ No roles to remove"
fi

echo "✅ Realm roles setup completed"
