#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"
CLIENT_YAML="${SCRIPT_DIR}/client.yaml"

# Load environment variables if .env exists
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

echo "📦 Creating clients in ${KEYCLOAK_REALM} from ${CLIENT_YAML}..."
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
echo "📄 Processing clients from ${CLIENT_YAML}..."

CLIENT_COUNT=$(yq '.m2m_clients | length' "$CLIENT_YAML")

for i in $(seq 0 $((CLIENT_COUNT - 1))); do
    CLIENT_ID=$(yq ".m2m_clients[$i].id" "$CLIENT_YAML")
    CLIENT_NAME=$(yq ".m2m_clients[$i].name" "$CLIENT_YAML")
    CLIENT_DESC=$(yq ".m2m_clients[$i].description" "$CLIENT_YAML")
    CLIENT_SECRET=$(yq ".m2m_clients[$i].secret" "$CLIENT_YAML")

    echo "🔍 Checking if client $CLIENT_ID exists..."
    CLIENT_CHECK=$(curl -s -H "Authorization: Bearer $TOKEN" \
        "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/clients?clientId=$CLIENT_ID")

    if [ "$(echo "$CLIENT_CHECK" | jq 'length')" -gt 0 ]; then
        echo "✅ Client $CLIENT_ID already exists, skipping creation"
        CLIENT_UUID=$(echo "$CLIENT_CHECK" | jq -r '.[0].id')
    else
        echo "📝 Creating client $CLIENT_ID..."
        CLIENT_DATA=$(jq -n \
            --arg clientId "$CLIENT_ID" \
            --arg name "$CLIENT_NAME" \
            --arg description "$CLIENT_DESC" \
            --arg secret "$CLIENT_SECRET" \
            '{clientId: $clientId, name: $name, description: $description, protocol: "openid-connect", publicClient: false, serviceAccountsEnabled: true, standardFlowEnabled: true, directAccessGrantsEnabled: false, enabled: true, secret: $secret}')

        CREATE_RESPONSE=$(curl -s -X POST "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/clients" \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d "$CLIENT_DATA" \
            -w "\n%{http_code}")

        HTTP_CODE=$(echo "$CREATE_RESPONSE" | tail -n1)

        if [ "$HTTP_CODE" = "201" ]; then
            echo "✅ Client $CLIENT_ID created successfully"
            CLIENT_CHECK=$(curl -s -H "Authorization: Bearer $TOKEN" \
                "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/clients?clientId=$CLIENT_ID")
            CLIENT_UUID=$(echo "$CLIENT_CHECK" | jq -r '.[0].id')
        else
            echo "❌ Failed to create client $CLIENT_ID"
            echo "Response: $CREATE_RESPONSE"
            exit 1
        fi
    fi

    # Add protocol mappers for client_id and client_name (JWT claims)
    echo "🔧 Adding protocol mappers for client_id and client_name to $CLIENT_ID..."

    # Protocol mapper for client_id (maps from "id" field in client.yaml)
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

    MAPPER_RESPONSE=$(curl -s -X POST "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/clients/$CLIENT_UUID/protocol-mappers/models" \
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

    # Protocol mapper for client_name (maps from "name" field in client.yaml)
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

    MAPPER_RESPONSE=$(curl -s -X POST "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/clients/$CLIENT_UUID/protocol-mappers/models" \
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

    # Assign service account roles
    ROLES_COUNT=$(yq ".m2m_clients[$i].service_account_roles | length" "$CLIENT_YAML")

    if [ "$ROLES_COUNT" != "null" ] && [ "$ROLES_COUNT" -gt 0 ]; then
        echo "🔑 Assigning service account roles to $CLIENT_ID..."

        SA_USER=$(curl -s -H "Authorization: Bearer $TOKEN" \
            "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/clients/$CLIENT_UUID/service-account-user")
        SA_USER_ID=$(echo "$SA_USER" | jq -r '.id')

        AVAILABLE_ROLES=$(curl -s -H "Authorization: Bearer $TOKEN" \
            "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/roles")

        ROLES_TO_ASSIGN="["
        for j in $(seq 0 $((ROLES_COUNT - 1))); do
            ROLE_NAME=$(yq ".m2m_clients[$i].service_account_roles[$j]" "$CLIENT_YAML")
            ROLE_OBJ=$(echo "$AVAILABLE_ROLES" | jq ".[] | select(.name == \"$ROLE_NAME\")")

            if [ -n "$ROLE_OBJ" ]; then
                if [ "$ROLES_TO_ASSIGN" != "[" ]; then
                    ROLES_TO_ASSIGN="$ROLES_TO_ASSIGN,"
                fi
                ROLES_TO_ASSIGN="$ROLES_TO_ASSIGN$ROLE_OBJ"
            else
                echo "⚠️  Role $ROLE_NAME not found, skipping"
            fi
        done
        ROLES_TO_ASSIGN="$ROLES_TO_ASSIGN]"

        if [ "$ROLES_TO_ASSIGN" != "[]" ]; then
            ASSIGN_RESPONSE=$(curl -s -X POST "${KEYCLOAK_BASE_URL}/admin/realms/${KEYCLOAK_REALM}/users/$SA_USER_ID/role-mappings/realm" \
                -H "Authorization: Bearer $TOKEN" \
                -H "Content-Type: application/json" \
                -d "$ROLES_TO_ASSIGN" \
                -w "\n%{http_code}")

            HTTP_CODE=$(echo "$ASSIGN_RESPONSE" | tail -n1)

            if [ "$HTTP_CODE" = "204" ] || [ "$HTTP_CODE" = "200" ]; then
                ROLE_NAMES=$(yq ".m2m_clients[$i].service_account_roles | join(\", \")" "$CLIENT_YAML")
                echo "✅ Roles assigned to $CLIENT_ID: $ROLE_NAMES"
            else
                echo "❌ Failed to assign roles to $CLIENT_ID"
                echo "Response: $ASSIGN_RESPONSE"
            fi
        fi
    fi
done

echo "✅ Clients setup completed"
