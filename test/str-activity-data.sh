#!/bin/bash

# Test script for activity data submission endpoint of the SDEP API
# Expects BACKEND_BASE_URL environment variable to be set
# Optionally accepts BEARER_TOKEN environment variable for authenticated requests
# Optionally accepts API_VERSION environment variable (defaults to v0)
# Tests POST /str/activity-data endpoint with valid activity data

set -e

if [ -z "$BACKEND_BASE_URL" ]; then
    echo "❌ Error: BACKEND_BASE_URL environment variable is not set"
    exit 1
fi

# Default API version to v0 if not set
API_VERSION=${API_VERSION:-v0}

# STR endpoint requires str01 client (str role)
# Load token from .bearer_token file
if [ -f .bearer_token ]; then
    BEARER_TOKEN=$(cat .bearer_token)
    echo "🔑 Loaded BEARER_TOKEN from .bearer_token"
else
    echo "⚠️  No .bearer_token file found"
fi

echo "🔍 Testing activity data submission endpoint at: ${BACKEND_BASE_URL}/api/${API_VERSION}/str/activity-data"

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

# Test 1: POST single activity data (amsterdam-myhouse-1)
echo "Test 1: POST single activity data (amsterdam-myhouse-1)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Generate dynamic timestamps to avoid duplicate key errors
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
END_TIME=$(date -u -d "+1 hour" +"%Y-%m-%dT%H:%M:%SZ")

# Prepare JSON payload
read -r -d '' PAYLOAD <<EOF || true
{
  "metadata": {
  },
  "activities": [
    {
      "url": "http://example.com/amsterdam-myhouse-1",
      "registrationNumber": "REG0002",
      "address": {
        "street": "Prinsengracht",
        "number": 265,
        "postalCode": "1016HV",
        "city": "Amsterdam"
      },
      "temporal": {
        "startDatetime": "$START_TIME",
        "endDatetime": "$END_TIME"
      },
      "areaId": "amsterdam-area-0363",
      "countryOfGuests": ["NLD", "DEU", "BEL"],
      "numberOfGuests": 4
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
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/activity-data")
else
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/activity-data")
fi

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

echo "Response: $body"
echo "HTTP Status: $http_code"
echo

if [ "$http_code" -eq 201 ]; then
    # Check if response contains success message
    if echo "$body" | grep -q "Successfully processed"; then
        echo "✅ Test 1 passed: Activity data successfully submitted"
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

# Test 2: POST multiple activities (rotterdam-myhouse-1, denhaag-myhouse-1)
echo "Test 2: POST multiple activities (rotterdam-myhouse-1, denhaag-myhouse-1)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Only run if authenticated
if [ -n "$BEARER_TOKEN" ]; then
    # Generate dynamic timestamps for multiple activities
    START_TIME_1=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    END_TIME_1=$(date -u -d "+1 hour" +"%Y-%m-%dT%H:%M:%SZ")
    START_TIME_2=$(date -u -d "+2 hours" +"%Y-%m-%dT%H:%M:%SZ")
    END_TIME_2=$(date -u -d "+3 hours" +"%Y-%m-%dT%H:%M:%SZ")

    # Prepare JSON payload with 2 activities similar to test data
    read -r -d '' PAYLOAD_MULTI <<EOF || true
{
  "metadata": {
  },
  "activities": [
    {
      "url": "http://example.com/rotterdam-myhouse-1",
      "registrationNumber": "REG0004",
      "address": {
        "street": "Witte de Withstraat",
        "number": 32,
        "postalCode": "3012BL",
        "city": "Rotterdam"
      },
      "temporal": {
        "startDatetime": "$START_TIME_1",
        "endDatetime": "$END_TIME_1"
      },
      "areaId": "rotterdam-area-0599",
      "countryOfGuests": ["NLD", "GBR"],
      "numberOfGuests": 2
    },
    {
      "url": "http://example.com/denhaag-myhouse-1",
      "registrationNumber": "REG0005",
      "address": {
        "street": "Noordeinde",
        "number": 70,
        "postalCode": "2514GK",
        "city": "Den Haag"
      },
      "temporal": {
        "startDatetime": "$START_TIME_2",
        "endDatetime": "$END_TIME_2"
      },
      "areaId": "denhaag-area-0518",
      "countryOfGuests": ["NLD", "FRA", "DEU"],
      "numberOfGuests": 6
    }
  ]
}
EOF

    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        -d "$PAYLOAD_MULTI" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/activity-data")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "Response: $body"
    echo "HTTP Status: $http_code"
    echo

    if [ "$http_code" -eq 201 ]; then
        # Check if response mentions 2 records
        if echo "$body" | grep -q "2"; then
            echo "✅ Test 2 passed: Multiple activities successfully submitted"
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

# Test 3: POST with validation error (missing required field)
echo "Test 3: POST with validation error (missing required field)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Only run if authenticated
if [ -n "$BEARER_TOKEN" ]; then
    # Generate dynamic timestamps
    START_TIME_3=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    END_TIME_3=$(date -u -d "+1 hour" +"%Y-%m-%dT%H:%M:%SZ")

    # Prepare invalid payload (missing 'url' field)
    read -r -d '' PAYLOAD_INVALID <<EOF || true
{
  "metadata": {
  },
  "activities": [
    {
      "registrationNumber": "REG9999",
      "address": {
        "street": "Prinsengracht",
        "number": 999,
        "postalCode": "1016HV",
        "city": "Amsterdam"
      },
      "temporal": {
        "startDatetime": "$START_TIME_3",
        "endDatetime": "$END_TIME_3"
      },
      "areaId": "amsterdam-area-0363",
      "countryOfGuests": ["NLD"],
      "numberOfGuests": 2
    }
  ]
}
EOF

    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        -d "$PAYLOAD_INVALID" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/activity-data")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "Response: $body"
    echo "HTTP Status: $http_code"
    echo

    if [ "$http_code" -eq 422 ]; then
        echo "✅ Test 3 passed: Validation error correctly returned (422)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "❌ Test 3 failed: Expected 422 but got $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo "⏭️  Skipping Test 3 (requires authentication)"
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
    echo "✅ All activity data endpoint tests passed!"
    exit 0
else
    echo "❌ Some activity data endpoint tests failed!"
    exit 1
fi
