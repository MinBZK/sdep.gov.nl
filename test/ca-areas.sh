#!/bin/bash

# Test script for area submission endpoint of the SDEP API
# Expects BACKEND_BASE_URL environment variable to be set
# Optionally accepts BEARER_TOKEN environment variable for authenticated requests
# Optionally accepts API_VERSION environment variable (defaults to v0)
# Tests POST /ca/areas endpoint with shapefile data

set -e

if [ -z "$BACKEND_BASE_URL" ]; then
    echo "❌ Error: BACKEND_BASE_URL environment variable is not set"
    exit 1
fi

# Default API version to v0 if not set
API_VERSION=${API_VERSION:-v0}

# CA endpoint requires authorized client
# Load token from ./tmp/.bearer_token_ca file
if [ -f ./tmp/.bearer_token ]; then
    BEARER_TOKEN=$(cat ./tmp/.bearer_token)
    echo "🔑 Loaded BEARER_TOKEN from ./tmp/.bearer_token"
else
    echo "⚠️  No ./tmp/.bearer_token file found"
fi

echo "🔍 Testing CA area endpoint at: ${BACKEND_BASE_URL}/api/${API_VERSION}/ca/areas"

# Check if BEARER_TOKEN is set
if [ -n "$BEARER_TOKEN" ]; then
    echo "🔑 Using Bearer token for authentication"
else
    echo "⚠️  No BEARER_TOKEN set - making unauthenticated request (should fail)"
fi
echo

# Track test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Check if test shapefile exists
SHAPEFILE_PATH="test-data/shapefiles/Amsterdam-dummy.zip"
if [ ! -f "$SHAPEFILE_PATH" ]; then
    echo "❌ Error: Test shapefile not found at $SHAPEFILE_PATH"
    exit 1
fi

echo "📂 Using test shapefile: $SHAPEFILE_PATH"
echo

# Encode file to base64
FILEDATA_BASE64=$(base64 -w 0 "$SHAPEFILE_PATH")

# Test 1: POST multiple areas
echo "Test 1: POST multiple areas (3 areas)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Generate unique area IDs
TIMESTAMP=$(date +%s)
AREA_ID_1="amsterdam-multi-area-${TIMESTAMP}-1"
AREA_ID_2="amsterdam-multi-area-${TIMESTAMP}-2"
AREA_ID_3="amsterdam-multi-area-${TIMESTAMP}-3"

# Prepare JSON payload with multiple areas
read -r -d '' PAYLOAD <<EOF || true
{
  "metadata": {},
  "areas": [
    {
      "areaId": "$AREA_ID_1",
      "filename": "Amsterdam-area-1.zip",
      "filedata": "$FILEDATA_BASE64"
    },
    {
      "areaId": "$AREA_ID_2",
      "filename": "Amsterdam-area-2.zip",
      "filedata": "$FILEDATA_BASE64"
    },
    {
      "areaId": "$AREA_ID_3",
      "filename": "Amsterdam-area-3.zip",
      "filedata": "$FILEDATA_BASE64"
    }
  ]
}
EOF

if [ -n "$BEARER_TOKEN" ]; then
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        -d "$PAYLOAD" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/ca/areas")
else
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/ca/areas")
fi

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

echo "Response: $body"
echo "HTTP Status: $http_code"
echo

if [ -n "$BEARER_TOKEN" ] && [ "$http_code" = "201" ]; then
    echo "✅ Test 1 passed"
    PASSED_TESTS=$((PASSED_TESTS + 1))
elif [ -z "$BEARER_TOKEN" ] && [ "$http_code" = "401" ]; then
    echo "✅ Test 1 passed (expected 401 without token)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo "❌ Test 1 failed (expected 201 with token or 401 without token, got $http_code)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi
echo

# Summary
echo "═══════════════════════════════════════════"
echo "Test Summary:"
echo "  Total:  $TOTAL_TESTS"
echo "  Passed: $PASSED_TESTS"
echo "  Failed: $FAILED_TESTS"
echo "═══════════════════════════════════════════"

if [ $FAILED_TESTS -gt 0 ]; then
    echo "❌ Some tests failed"
    exit 1
else
    echo "✅ All tests passed"
    exit 0
fi
