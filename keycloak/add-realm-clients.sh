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

if [ -z "${KC_APP_REALM_ADMIN_ID:-}" ]; then
    echo "❌ Error: KC_APP_REALM_ADMIN_ID is not set"
    exit 1
fi

if [ -z "${KC_APP_REALM_ADMIN_SECRET:-}" ]; then
    echo "❌ Error: KC_APP_REALM_ADMIN_SECRET is not set"
    exit 1
fi

if [ -z "${KC_APP_REALM_CLIENT_YAML:-}" ]; then
    echo "❌ Error: KC_APP_REALM_CLIENT_YAML is not set"
    exit 1
fi

if [ ! -f "${KC_APP_REALM_CLIENT_YAML}" ]; then
    echo "❌ Error: KC_APP_REALM_CLIENT_YAML file not found: ${KC_APP_REALM_CLIENT_YAML}"
    exit 1
fi

echo "📦 Creating clients in ${KC_APP_REALM} from ${KC_APP_REALM_CLIENT_YAML}..."
echo "🔐 Authenticating with realm admin service account..."

TOKEN_RESPONSE=$(curl -s -X POST "${KC_BASE_URL}/realms/${KC_APP_REALM}/protocol/openid-connect/token" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_id=${KC_APP_REALM_ADMIN_ID}" \
    -d "client_secret=${KC_APP_REALM_ADMIN_SECRET}" \
    -d "grant_type=client_credentials")

TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to authenticate with realm admin service account"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Authentication successful"
echo "📄 Processing clients from ${KC_APP_REALM_CLIENT_YAML}..."

CLIENT_COUNT=$(yq '.clients | length' "$KC_APP_REALM_CLIENT_YAML")
REALM_PREFIX="${KC_APP_REALM}-"

# First pass: validate all clients have REALM prefix
for i in $(seq 0 $((CLIENT_COUNT - 1))); do
    CLIENT_ID=$(yq ".clients[$i].id" "$KC_APP_REALM_CLIENT_YAML")

    # Validate that client ID has REALM prefix
    if [[ ! "$CLIENT_ID" =~ ^${REALM_PREFIX} ]]; then
        echo "❌ Error: Client ID '$CLIENT_ID' does not have required prefix '${REALM_PREFIX}'"
        echo "All client IDs in YAML must start with '${REALM_PREFIX}'"
        exit 1
    fi
done

# Second pass: process clients
for i in $(seq 0 $((CLIENT_COUNT - 1))); do
    CLIENT_ID=$(yq ".clients[$i].id" "$KC_APP_REALM_CLIENT_YAML")
    CLIENT_NAME=$(yq ".clients[$i].name" "$KC_APP_REALM_CLIENT_YAML")
    CLIENT_DESC=$(yq ".clients[$i].description" "$KC_APP_REALM_CLIENT_YAML")
    CLIENT_SECRET=$(yq ".clients[$i].secret" "$KC_APP_REALM_CLIENT_YAML")

    echo "🔍 Checking if client $CLIENT_ID exists..."
    CLIENT_CHECK=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/clients?clientId=$CLIENT_ID")

    if [ "$(echo "$CLIENT_CHECK" | jq 'length')" -gt 0 ]; then
        echo "✅ Client $CLIENT_ID already exists, skipping creation"
        CLIENT_UUID=$(echo "$CLIENT_CHECK" | jq -r '.[0].id')
    else
        echo "📝 Creating client $CLIENT_ID..."

        # Build CLIENT_DATA with or without secret depending on whether it's defined
        if [ "$CLIENT_SECRET" != "null" ] && [ -n "$CLIENT_SECRET" ]; then
            CLIENT_DATA=$(jq -n \
                --arg clientId "$CLIENT_ID" \
                --arg name "$CLIENT_NAME" \
                --arg description "$CLIENT_DESC" \
                --arg secret "$CLIENT_SECRET" \
                '{clientId: $clientId, name: $name, description: $description, protocol: "openid-connect", publicClient: false, serviceAccountsEnabled: true, standardFlowEnabled: false, directAccessGrantsEnabled: false, enabled: true, secret: $secret}')
        else
            CLIENT_DATA=$(jq -n \
                --arg clientId "$CLIENT_ID" \
                --arg name "$CLIENT_NAME" \
                --arg description "$CLIENT_DESC" \
                '{clientId: $clientId, name: $name, description: $description, protocol: "openid-connect", publicClient: false, serviceAccountsEnabled: true, standardFlowEnabled: false, directAccessGrantsEnabled: false, enabled: true}')
        fi

        CREATE_RESPONSE=$(curl -s -X POST "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/clients" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$CLIENT_DATA" \
            -w "\n%{http_code}")

        HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)

        if [ "$HTTP_CODE" = "201" ]; then
            echo "✅ Client $CLIENT_ID created successfully"
            CLIENT_CHECK=$(curl -s -H "Authorization: Bearer $TOKEN" \
                "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/clients?clientId=$CLIENT_ID")
            CLIENT_UUID=$(echo "$CLIENT_CHECK" | jq -r '.[0].id')

            # Retrieve the generated secret from Keycloak
            CLIENT_SECRET_RESPONSE=$(curl -s -H "Authorization: Bearer $TOKEN" \
                "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/clients/$CLIENT_UUID/client-secret")
            GENERATED_SECRET=$(echo "$CLIENT_SECRET_RESPONSE" | jq -r '.value')

            # echo "🔑 Secret for $CLIENT_ID: $GENERATED_SECRET"
        else
            echo "❌ Failed to create client $CLIENT_ID"
            echo "Response: $CREATE_RESPONSE"
            exit 1
        fi
    fi

    # Add protocol mappers for client_id and client_name (JWT claims)
    echo "🔧 Adding protocol mappers for client_id and client_name to $CLIENT_ID..."

    # Protocol mapper for client_id (maps from "id" field in clients.yaml)
    CLIENT_ID_MAPPER=$(jq -n \
        --arg clientId "$CLIENT_ID" \
        '{
            name: "client_id",
            protocol: "openid-connect",
            protocolMapper: "oidc-hardcoded-claim-mapper",
            consentRequired: false,
            config: {
                "claim.name": "client_id",
                "claim.value": $clientId,
                "jsonType.label": "String",
                "id.token.claim": "false",
                "access.token.claim": "true",
                "userinfo.token.claim": "false"
            }
        }')

    MAPPER_RESPONSE=$(curl -s -X POST "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/clients/$CLIENT_UUID/protocol-mappers/models" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "$CLIENT_ID_MAPPER" \
        -w "\n%{http_code}")

    HTTP_CODE=$(echo "$MAPPER_RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "409" ]; then
        echo "✅ client_id mapper added/exists for $CLIENT_ID"
    else
        echo "⚠️  Failed to add client_id mapper (non-critical)"
        echo "Response: $MAPPER_RESPONSE"
    fi

    # Protocol mapper for client_name (maps from "name" field in clients.yaml)
    CLIENT_NAME_MAPPER=$(jq -n \
        --arg clientName "$CLIENT_NAME" \
        '{
            name: "client_name",
            protocol: "openid-connect",
            protocolMapper: "oidc-hardcoded-claim-mapper",
            consentRequired: false,
            config: {
                "claim.name": "client_name",
                "claim.value": $clientName,
                "jsonType.label": "String",
                "id.token.claim": "false",
                "access.token.claim": "true",
                "userinfo.token.claim": "false"
            }
        }')

    MAPPER_RESPONSE=$(curl -s -X POST "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/clients/$CLIENT_UUID/protocol-mappers/models" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "$CLIENT_NAME_MAPPER" \
        -w "\n%{http_code}")

    HTTP_CODE=$(echo "$MAPPER_RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "409" ]; then
        echo "✅ client_name mapper added/exists for $CLIENT_ID"
    else
        echo "⚠️  Failed to add client_name mapper (non-critical)"
        echo "Response: $MAPPER_RESPONSE"
    fi

    # Manage service account roles (idempotent and declarative)
    ROLES_COUNT=$(yq ".clients[$i].service_account_roles | length" "$KC_APP_REALM_CLIENT_YAML")

    if [ "$ROLES_COUNT" != "null" ] && [ "$ROLES_COUNT" -gt 0 ]; then
        echo "🔑 Managing service account roles for $CLIENT_ID..."

        # Get service account user
        SA_USER=$(curl -s -H "Authorization: Bearer $TOKEN" \
            "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/clients/$CLIENT_UUID/service-account-user")
        SA_USER_ID=$(echo "$SA_USER" | jq -r '.id')

        # Get available roles in realm
        AVAILABLE_ROLES=$(curl -s -H "Authorization: Bearer $TOKEN" \
            "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/roles")

        # Get currently assigned realm roles for service account
        CURRENT_ROLES=$(curl -s -H "Authorization: Bearer $TOKEN" \
            "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/users/$SA_USER_ID/role-mappings/realm")

        # Build desired roles array from YAML (validate all roles exist)
        DESIRED_ROLES="["
        for j in $(seq 0 $((ROLES_COUNT - 1))); do
            ROLE_NAME=$(yq ".clients[$i].service_account_roles[$j]" "$KC_APP_REALM_CLIENT_YAML")
            ROLE_OBJ=$(echo "$AVAILABLE_ROLES" | jq ".[] | select(.name == \"$ROLE_NAME\")")

            if [ -z "$ROLE_OBJ" ]; then
                echo "❌ Error: Role $ROLE_NAME not found for client $CLIENT_ID"
                exit 1
            fi

            if [ "$DESIRED_ROLES" != "[" ]; then
                DESIRED_ROLES="$DESIRED_ROLES,"
            fi
            DESIRED_ROLES="$DESIRED_ROLES$ROLE_OBJ"
        done
        DESIRED_ROLES="$DESIRED_ROLES]"

        # Calculate roles to ADD (in desired but not in current)
        ROLES_TO_ADD=$(jq -n \
            --argjson desired "$DESIRED_ROLES" \
            --argjson current "$CURRENT_ROLES" \
            '$desired - ($desired - ($desired - $current))')

        # Calculate roles to REMOVE (in current but not in desired)
        ROLES_TO_REMOVE=$(jq -n \
            --argjson desired "$DESIRED_ROLES" \
            --argjson current "$CURRENT_ROLES" \
            '$current - ($current - ($current - $desired))')

        # Add missing roles
        if [ "$(echo "$ROLES_TO_ADD" | jq 'length')" -gt 0 ]; then
            ADD_RESPONSE=$(curl -s -X POST "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/users/$SA_USER_ID/role-mappings/realm" \
                -H "Authorization: Bearer $TOKEN" \
                -H "Content-Type: application/json" \
                -d "$ROLES_TO_ADD" \
                -w "\n%{http_code}")

            HTTP_CODE=$(echo "$ADD_RESPONSE" | tail -n1)

            if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
                ADDED_NAMES=$(echo "$ROLES_TO_ADD" | jq -r '[.[].name] | join(", ")')
                echo "✅ Added roles to $CLIENT_ID: $ADDED_NAMES"
            else
                echo "❌ Failed to add roles to $CLIENT_ID"
                echo "Response: $ADD_RESPONSE"
                exit 1
            fi
        fi

        # Remove obsolete roles
        if [ "$(echo "$ROLES_TO_REMOVE" | jq 'length')" -gt 0 ]; then
            REMOVE_RESPONSE=$(curl -s -X DELETE "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/users/$SA_USER_ID/role-mappings/realm" \
                -H "Authorization: Bearer $TOKEN" \
                -H "Content-Type: application/json" \
                -d "$ROLES_TO_REMOVE" \
                -w "\n%{http_code}")

            HTTP_CODE=$(echo "$REMOVE_RESPONSE" | tail -n1)

            if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
                REMOVED_NAMES=$(echo "$ROLES_TO_REMOVE" | jq -r '[.[].name] | join(", ")')
                echo "✅ Removed roles from $CLIENT_ID: $REMOVED_NAMES"
            else
                echo "❌ Failed to remove roles from $CLIENT_ID"
                echo "Response: $REMOVE_RESPONSE"
                exit 1
            fi
        fi

        # Report if no changes needed
        if [ "$(echo "$ROLES_TO_ADD" | jq 'length')" -eq 0 ] && [ "$(echo "$ROLES_TO_REMOVE" | jq 'length')" -eq 0 ]; then
            ROLE_NAMES=$(yq ".clients[$i].service_account_roles | join(\", \")" "$KC_APP_REALM_CLIENT_YAML")
            echo "✅ Roles already in sync for $CLIENT_ID: $ROLE_NAMES"
        fi
    fi
done

# Remove clients with REALM prefix that are not in YAML
echo "🔍 Checking for clients to remove..."

# Build list of desired client IDs
DESIRED_CLIENT_IDS="["
for i in $(seq 0 $((CLIENT_COUNT - 1))); do
    CLIENT_ID=$(yq ".clients[$i].id" "$KC_APP_REALM_CLIENT_YAML")
    if [ "$DESIRED_CLIENT_IDS" != "[" ]; then
        DESIRED_CLIENT_IDS="$DESIRED_CLIENT_IDS,"
    fi
    DESIRED_CLIENT_IDS="$DESIRED_CLIENT_IDS\"$CLIENT_ID\""
done
DESIRED_CLIENT_IDS="$DESIRED_CLIENT_IDS]"

# Get all clients in realm
ALL_CLIENTS=$(curl -s -H "Authorization: Bearer $TOKEN" \
    "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/clients")

# Find clients with REALM prefix that are not in YAML
CLIENTS_TO_REMOVE=$(echo "$ALL_CLIENTS" | jq -r --argjson desired "$DESIRED_CLIENT_IDS" --arg prefix "${REALM_PREFIX}" \
    '[.[] | select(.clientId | startswith($prefix)) | select([.clientId] | inside($desired) | not) | {id: .id, clientId: .clientId}] | .[]')

if [ -n "$CLIENTS_TO_REMOVE" ]; then
    echo "$CLIENTS_TO_REMOVE" | jq -c '.' | while IFS= read -r CLIENT_OBJ; do
        CLIENT_UUID=$(echo "$CLIENT_OBJ" | jq -r '.id')
        CLIENT_ID=$(echo "$CLIENT_OBJ" | jq -r '.clientId')

        echo "🗑️  Removing client $CLIENT_ID (not in YAML)..."
        DELETE_RESPONSE=$(curl -s -X DELETE "${KC_BASE_URL}/admin/realms/${KC_APP_REALM}/clients/$CLIENT_UUID" \
            -H "Authorization: Bearer $TOKEN" \
            -w "%{http_code}")

        if [ "$DELETE_RESPONSE" = "204" ] || [ "$DELETE_RESPONSE" = "200" ]; then
            echo "✅ Client $CLIENT_ID removed successfully"
        else
            echo "❌ Failed to remove client $CLIENT_ID"
            echo "Response: $DELETE_RESPONSE"
            exit 1
        fi
    done
else
    echo "✅ No clients to remove"
fi

echo "✅ Clients setup completed"
