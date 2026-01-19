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

# Test 1: POST single area
echo "Test 1: POST single area (amsterdam-single-area-1)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Generate unique area ID
TIMESTAMP=$(date +%s)
AREA_ID_SINGLE="amsterdam-single-area-${TIMESTAMP}"

# Prepare JSON payload with single area
read -r -d '' PAYLOAD <<EOF || true
{
  "metadata": {},
  "areas": [
    {
      "competentAuthorityAreaId": "$AREA_ID_SINGLE",
      "filename": "Amsterdam-area-single.zip",
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

if [ "$http_code" -eq 201 ]; then
    # Check for new response format with totalProcessed, succeeded, failed
    if echo "$body" | grep -q '"totalProcessed":1' && \
       echo "$body" | grep -q '"succeeded":1' && \
       echo "$body" | grep -q '"failed":0'; then
        echo "✅ Test 1 passed: Area successfully submitted"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "❌ Test 1 failed: Expected success message in response"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
elif [ "$http_code" -eq 401 ] && [ -z "$BEARER_TOKEN" ]; then
    echo "✅ Test 1 passed: Correctly rejected unauthenticated request (401)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo "❌ Test 1 failed: Unexpected HTTP status $http_code"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo

# Test 2: POST multiple areas (rotterdam-area-1, denhaag-area-1)
echo "Test 2: POST multiple areas (rotterdam-area-1, denhaag-area-1)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Only run if authenticated
if [ -n "$BEARER_TOKEN" ]; then
    # Generate unique competent authority area IDs
    TIMESTAMP=$(date +%s)
    AREA_ID_1="rotterdam-multi-area-${TIMESTAMP}-1"
    AREA_ID_2="denhaag-multi-area-${TIMESTAMP}-2"

    # Prepare JSON payload with 2 areas similar to test data
    read -r -d '' PAYLOAD_MULTI <<EOF || true
{
  "metadata": {},
  "areas": [
    {
      "competentAuthorityAreaId": "$AREA_ID_1",
      "filename": "Rotterdam-area-1.zip",
      "filedata": "$FILEDATA_BASE64"
    },
    {
      "competentAuthorityAreaId": "$AREA_ID_2",
      "filename": "DenHaag-area-2.zip",
      "filedata": "$FILEDATA_BASE64"
    }
  ]
}
EOF

    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        -d "$PAYLOAD_MULTI" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/ca/areas")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "Response: $body"
    echo "HTTP Status: $http_code"
    echo

    if [ "$http_code" -eq 201 ]; then
        # Check for new response format
        if echo "$body" | grep -q '"totalProcessed":2' && \
           echo "$body" | grep -q '"succeeded":2' && \
           echo "$body" | grep -q '"failed":0'; then
            echo "✅ Test 2 passed: Multiple areas successfully submitted"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo "❌ Test 2 failed: Expected message about 2 records"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        echo "❌ Test 2 failed: Unexpected HTTP status $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo "⏭️  Skipping Test 2 (requires authentication)"
fi

echo

# Test 3: POST with optional competentAuthorityAreaId field
echo "Test 3: POST with optional competentAuthorityAreaId field"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Only run if authenticated
if [ -n "$BEARER_TOKEN" ]; then
    # Generate unique ID using epoch timestamp to ensure test idempotence
    UNIQUE_ID=$(date +%s%N | cut -b1-13)

    # Prepare payload with custom competentAuthorityAreaId
    read -r -d '' PAYLOAD_WITH_ID <<EOF || true
{
  "metadata": {},
  "areas": [
    {
      "competentAuthorityAreaId": "custom-area-id-$UNIQUE_ID",
      "filename": "Amsterdam-with-id-$UNIQUE_ID.zip",
      "filedata": "$FILEDATA_BASE64"
    }
  ]
}
EOF

    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        -d "$PAYLOAD_WITH_ID" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/ca/areas")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "Response: $body"
    echo "HTTP Status: $http_code"
    echo

    if [ "$http_code" -eq 201 ]; then
        # Check for new response format
        if echo "$body" | grep -q '"totalProcessed":1' && \
           echo "$body" | grep -q '"succeeded":1' && \
           echo "$body" | grep -q '"failed":0'; then
            echo "✅ Test 3 passed: Area with custom competentAuthorityAreaId successfully submitted"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo "❌ Test 3 failed: Expected success response format"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        echo "❌ Test 3 failed: Expected 201 but got $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo "⏭️  Skipping Test 3 (requires authentication)"
fi

echo

# Test 4: POST with validation error (missing required field)
echo "Test 4: POST with validation error (missing required field)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Only run if authenticated
if [ -n "$BEARER_TOKEN" ]; then
    # Prepare invalid payload (missing 'filedata' field)
    read -r -d '' PAYLOAD_INVALID <<EOF || true
{
  "metadata": {},
  "areas": [
    {
      "competentAuthorityAreaId": "invalid-area-9999",
      "filename": "Invalid-area.zip"
    }
  ]
}
EOF

    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        -d "$PAYLOAD_INVALID" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/ca/areas")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "Response: $body"
    echo "HTTP Status: $http_code"
    echo

    if [ "$http_code" -eq 422 ]; then
        # Check for new response format - all failed
        if echo "$body" | grep -q '"totalProcessed":1' && \
           echo "$body" | grep -q '"succeeded":0' && \
           echo "$body" | grep -q '"failed":1' && \
           echo "$body" | grep -q '"failures"'; then
            echo "✅ Test 4 passed: Validation error correctly returned (422) all submitted entries got validation errors"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo "❌ Test 4 failed: Expected 422 with proper failure response format"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        echo "❌ Test 4 failed: Expected 422 but got $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo "⏭️  Skipping Test 4 (requires authentication)"
fi

echo

# Test 5: POST with partial success (some succeed, some fail)
echo "Test 5: POST with partial success (mix of valid and invalid)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Only run if authenticated
if [ -n "$BEARER_TOKEN" ]; then
    UNIQUE_ID=$(date +%s%N | cut -b1-13)

    # Prepare payload with 2 areas: 1 valid, 1 invalid (missing filedata)
    read -r -d '' PAYLOAD_PARTIAL <<EOF || true
{
  "metadata": {},
  "areas": [
    {
      "competentAuthorityAreaId": "partial-valid-$UNIQUE_ID",
      "filename": "Valid-area.zip",
      "filedata": "$FILEDATA_BASE64"
    },
    {
      "competentAuthorityAreaId": "partial-invalid-$UNIQUE_ID",
      "filename": "Invalid-area.zip"
    }
  ]
}
EOF

    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        -d "$PAYLOAD_PARTIAL" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/ca/areas")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "Response: $body"
    echo "HTTP Status: $http_code"
    echo

    # Expect 200 OK (partial success)
    if [ "$http_code" -eq 200 ]; then
        # Check for partial success: 1 succeeded, 1 failed
        if echo "$body" | grep -q '"totalProcessed":2' && \
           echo "$body" | grep -q '"succeeded":1' && \
           echo "$body" | grep -q '"failed":1' && \
           echo "$body" | grep -q '"failures"'; then
            echo "✅ Test 5 passed: Partial success correctly returned (200) - 1 succeeded, 1 failed"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo "❌ Test 5 failed: Expected partial success response format"
            echo "   Expected: totalProcessed=2, succeeded=1, failed=1 with failures list"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        echo "❌ Test 5 failed: Expected 200 but got $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo "⏭️  Skipping Test 5 (requires authentication)"
fi

echo

# Summary
echo "═══════════════════════════════════════"
echo "Test Summary:"
echo "  Total:  $TOTAL_TESTS"
echo "  Passed: $PASSED_TESTS ✅"
echo "  Failed: $FAILED_TESTS ❌"
echo "═══════════════════════════════════════"

if [ $FAILED_TESTS -eq 0 ]; then
    echo "✅ All area endpoint tests passed!"
    exit 0
else
    echo "❌ Some area endpoint tests failed!"
    exit 1
fi
