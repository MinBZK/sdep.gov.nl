#!/bin/bash

# Test script for activity submission endpoint of the SDEP API
# Expects BACKEND_BASE_URL environment variable to be set
# Optionally accepts BEARER_TOKEN environment variable for authenticated requests
# Optionally accepts API_VERSION environment variable (defaults to v0)
# Tests POST /str/activities endpoint with valid activities

set -e

if [ -z "$BACKEND_BASE_URL" ]; then
    echo "❌ Error: BACKEND_BASE_URL environment variable is not set"
    exit 1
fi

# Default API version to v0 if not set
API_VERSION=${API_VERSION:-v0}

# STR endpoint requires authorized client
# Load token from ./tmp/.bearer_token file
if [ -f ./tmp/.bearer_token ]; then
    BEARER_TOKEN=$(cat ./tmp/.bearer_token)
    echo "🔑 Loaded BEARER_TOKEN from ./tmp/.bearer_token"
else
    echo "⚠️  No ./tmp/.bearer_token file found"
fi

echo "🔍 Testing STR activity endpoints at: ${BACKEND_BASE_URL}/api/${API_VERSION}/str/activities"

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

# Fetch real area IDs to use in tests
echo "📍 Fetching real area IDs from API..."
if [ -n "$BEARER_TOKEN" ]; then
    areas_response=$(curl -s \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/areas?limit=3")

    AREA_ID_1=$(echo "$areas_response" | jq -r '.areas[0].areaId // empty' 2>/dev/null)
    AREA_ID_2=$(echo "$areas_response" | jq -r '.areas[1].areaId // empty' 2>/dev/null)
    AREA_ID_3=$(echo "$areas_response" | jq -r '.areas[2].areaId // empty' 2>/dev/null)

    if [ -z "$AREA_ID_1" ] || [ -z "$AREA_ID_2" ] || [ -z "$AREA_ID_3" ]; then
        echo "❌ Error: Could not fetch area IDs from API"
        exit 1
    fi

    echo "✅ Fetched area IDs: $AREA_ID_1, $AREA_ID_2, $AREA_ID_3"
else
    echo "⚠️  No token available, using placeholder IDs (tests will fail)"
    AREA_ID_1="00000000-0000-0000-0000-000000000001"
    AREA_ID_2="00000000-0000-0000-0000-000000000002"
    AREA_ID_3="00000000-0000-0000-0000-000000000003"
fi
echo

# Test 1: POST single activity (amsterdam-myhouse-1)
echo "Test 1: POST single activity (amsterdam-myhouse-1)"
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
      "areaId": "$AREA_ID_1",
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
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/activities")
else
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -d "$PAYLOAD" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/activities")
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
        echo "✅ Test 1 passed: Activity successfully submitted"
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
      "areaId": "$AREA_ID_2",
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
      "areaId": "$AREA_ID_3",
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
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/activities")

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

# Test 3: POST with optional activityId field
echo "Test 3: POST with optional activityId field"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Only run if authenticated
if [ -n "$BEARER_TOKEN" ]; then
    # Generate dynamic timestamps with offset to avoid collisions with Test 1 and 2
    START_TIME_3=$(date -u -d "+4 hours" +"%Y-%m-%dT%H:%M:%SZ")
    END_TIME_3=$(date -u -d "+5 hours" +"%Y-%m-%dT%H:%M:%SZ")

    # Generate unique URL using epoch timestamp to ensure test idempotence
    UNIQUE_ID=$(date +%s%N | cut -b1-12)

    # Prepare payload with activityId
    read -r -d '' PAYLOAD_WITH_ID <<EOF || true
{
  "metadata": {
  },
  "activities": [
    {
      "activityId": "550e8400-e29b-41d4-a716-$UNIQUE_ID",
      "url": "http://example.com/amsterdam-with-id-$UNIQUE_ID",
      "registrationNumber": "REGID001",
      "address": {
        "street": "Prinsengracht",
        "number": 267,
        "postalCode": "1016HV",
        "city": "Amsterdam"
      },
      "temporal": {
        "startDatetime": "$START_TIME_3",
        "endDatetime": "$END_TIME_3"
      },
      "areaId": "$AREA_ID_1",
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
        -d "$PAYLOAD_WITH_ID" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/activities")

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
            echo "✅ Test 3 passed: Activity with custom activityId successfully submitted"
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
    # Generate dynamic timestamps with offset to avoid collisions
    START_TIME_4=$(date -u -d "+6 hours" +"%Y-%m-%dT%H:%M:%SZ")
    END_TIME_4=$(date -u -d "+7 hours" +"%Y-%m-%dT%H:%M:%SZ")

    # Prepare invalid payload (missing 'registrationNumber' required field)
    read -r -d '' PAYLOAD_INVALID <<EOF || true
{
  "metadata": {
  },
  "activities": [
    {
      "url": "http://example.com/amsterdam-invalid",
      "address": {
        "street": "Prinsengracht",
        "number": 999,
        "postalCode": "1016HV",
        "city": "Amsterdam"
      },
      "temporal": {
        "startDatetime": "$START_TIME_4",
        "endDatetime": "$END_TIME_4"
      },
      "areaId": "$AREA_ID_1",
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
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/activities")

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
    # Generate dynamic timestamps
    START_TIME_5=$(date -u -d "+8 hours" +"%Y-%m-%dT%H:%M:%SZ")
    END_TIME_5=$(date -u -d "+9 hours" +"%Y-%m-%dT%H:%M:%SZ")
    UNIQUE_ID=$(date +%s%N | cut -b1-13)

    # Prepare payload with 2 activities: 1 valid, 1 invalid area
    read -r -d '' PAYLOAD_PARTIAL <<EOF || true
{
  "metadata": {},
  "activities": [
    {
      "url": "http://example.com/partial-valid-$UNIQUE_ID",
      "registrationNumber": "REGPART001",
      "address": {
        "street": "Valid Street",
        "number": 100,
        "postalCode": "1000AA",
        "city": "Amsterdam"
      },
      "temporal": {
        "startDatetime": "$START_TIME_5",
        "endDatetime": "$END_TIME_5"
      },
      "areaId": "$AREA_ID_1",
      "numberOfGuests": 2
    },
    {
      "url": "http://example.com/partial-invalid-area-$UNIQUE_ID",
      "registrationNumber": "REGPART002",
      "address": {
        "street": "Invalid Area Street",
        "number": 200,
        "postalCode": "2000BB",
        "city": "Nowhere"
      },
      "temporal": {
        "startDatetime": "$START_TIME_5",
        "endDatetime": "$END_TIME_5"
      },
      "areaId": "00000000-0000-0000-0000-000000000000",
      "numberOfGuests": 3
    }
  ]
}
EOF

    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        -d "$PAYLOAD_PARTIAL" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/activities")

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
    echo "✅ All activity endpoint tests passed!"
    exit 0
else
    echo "❌ Some activity endpoint tests failed!"
    exit 1
fi
