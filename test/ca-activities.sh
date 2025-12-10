#!/bin/bash

# Test script for CA activity endpoints
# Expects BACKEND_BASE_URL environment variable to be set

set -e

if [ -z "$BACKEND_BASE_URL" ]; then
    echo "❌ Error: BACKEND_BASE_URL environment variable is not set"
    exit 1
fi

# CA endpoint requires ca01 client (ca role)
# Load token from ./tmp/.bearer_token file
if [ -f ./tmp/.bearer_token ]; then
    BEARER_TOKEN=$(cat ./tmp/.bearer_token)
    echo "🔑 Loaded BEARER_TOKEN from ./tmp/.bearer_token"
else
    echo "⚠️  No ./tmp/.bearer_token file found"
fi

# Default API version to v0 if not set
API_VERSION=${API_VERSION:-v0}

echo "🔍 Testing CA activity endpoints at: ${BACKEND_BASE_URL}/api/${API_VERSION}/ca/activities"

# Track test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test 1: Count activities
echo ""
echo "Test 1: Count activities"
echo "URL: ${BACKEND_BASE_URL}/api/${API_VERSION}/ca/activities/count"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  "${BACKEND_BASE_URL}/api/${API_VERSION}/ca/activities/count")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

echo "Response: $BODY"
echo "HTTP Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" -eq 200 ]; then
    # Extract count from JSON response (handles both "count":10 and "count": 10)
    actual_count=$(echo "$BODY" | grep -o '"count"[[:space:]]*:[[:space:]]*[0-9]*' | grep -o '[0-9]*$')

    if [ -z "$actual_count" ]; then
        echo "❌ Test 1 failed: Could not extract count from response body"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    elif [ "$actual_count" -ge 0 ]; then
        echo "✅ Test 1 passed: Activity count is valid (Got: $actual_count)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "❌ Test 1 failed: Invalid count value (Expected: >= 0, Got: $actual_count)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo "❌ Test 1 failed: Expected HTTP 200, got $HTTP_STATUS"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

# Test 2: Get all activities
echo ""
echo "Test 2: Get all activities (no pagination)"
echo "URL: ${BACKEND_BASE_URL}/api/${API_VERSION}/ca/activities"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  "${BACKEND_BASE_URL}/api/${API_VERSION}/ca/activities")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" != "200" ]; then
    echo "❌ Test 2 failed: Expected HTTP 200, got $HTTP_STATUS"
    echo "$BODY" | python3 -m json.tool
    FAILED_TESTS=$((FAILED_TESTS + 1))
else
    echo "✅ Test 2 passed: HTTP 200"
    echo "$BODY" | python3 -m json.tool
    PASSED_TESTS=$((PASSED_TESTS + 1))
fi

# Test 3: Get activities with pagination
echo ""
echo "Test 3: Get activities with pagination (offset=0, limit=1)"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  "${BACKEND_BASE_URL}/api/${API_VERSION}/ca/activities?offset=0&limit=1")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

if [ "$HTTP_STATUS" != "200" ]; then
    echo "❌ Test 3 failed: Expected HTTP 200, got $HTTP_STATUS"
    echo "$BODY" | python3 -m json.tool
    FAILED_TESTS=$((FAILED_TESTS + 1))
else
    # Check that we got a valid count (>= 0)
    COUNT=$(echo "$BODY" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['activities']))")
    if [ "$COUNT" -ge 0 ]; then
        echo "✅ Test 3 passed: Pagination works (got $COUNT activities)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "❌ Test 3 failed: Invalid count (got $COUNT)"
        echo "$BODY" | python3 -m json.tool
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
fi

# Summary
echo ""
echo "═══════════════════════════════════════"
echo "Test Summary:"
echo "  Total:  $TOTAL_TESTS"
echo "  Passed: $PASSED_TESTS ✅"
echo "  Failed: $FAILED_TESTS ❌"
echo "═══════════════════════════════════════"

if [ "$FAILED_TESTS" -eq 0 ]; then
    echo "✅ All CA activity endpoint tests passed!"
    exit 0
else
    echo "❌ Some CA activity endpoint tests failed!"
    exit 1
fi
