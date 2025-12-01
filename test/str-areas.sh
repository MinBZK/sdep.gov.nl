#!/bin/bash

# Test script for STR areas endpoints of the SDEP API
# Expects BACKEND_BASE_URL environment variable to be set
# Optionally accepts BEARER_TOKEN environment variable for authenticated requests
# Optionally accepts API_VERSION environment variable (defaults to v0)
# Tests:
#   - GET /str/areas/count (count areas)
#   - GET /str/areas (list areas with optional pagination)
#   - GET /str/area/{areaId} (get specific area shapefile data)

set -e

if [ -z "$BACKEND_BASE_URL" ]; then
    echo "❌ Error: BACKEND_BASE_URL environment variable is not set"
    exit 1
fi

# Default API version to v0 if not set
API_VERSION=${API_VERSION:-v0}

# If BEARER_TOKEN is not set, try to read from token file
if [ -z "$BEARER_TOKEN" ]; then
    TOKEN_FILE="${TOKEN_FILE:-.bearer_token}"
    if [ -f "$TOKEN_FILE" ]; then
        BEARER_TOKEN=$(cat "$TOKEN_FILE")
        echo "🔑 Loaded BEARER_TOKEN from $TOKEN_FILE"
    fi
fi

echo "🔍 Testing STR areas endpoints"

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

##############################################################################
# GET /str/areas/count - Count areas test
##############################################################################

echo "════════════════════════════════════════════"
echo "Testing GET /str/areas/count (count areas)"
echo "════════════════════════════════════════════"
echo

# Test 1: Count areas
echo "Test 1: Count areas (should be 3)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

if [ -n "$BEARER_TOKEN" ]; then
    response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/areas/count")
else
    response=$(curl -s -w "\n%{http_code}" "${BACKEND_BASE_URL}/api/${API_VERSION}/str/areas/count")
fi

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

echo "Response: $body"
echo "HTTP Status: $http_code"
echo

# Expected count
EXPECTED_COUNT=3

if [ "$http_code" -eq 200 ]; then
    # Extract count from JSON response (handles both "count":10 and "count": 10)
    actual_count=$(echo "$body" | grep -o '"count"[[:space:]]*:[[:space:]]*[0-9]*' | grep -o '[0-9]*$')

    if [ -z "$actual_count" ]; then
        echo "❌ Test 1 failed: Could not extract count from response body"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    elif [ "$actual_count" -eq "$EXPECTED_COUNT" ]; then
        echo "✅ Test 1 passed: Areas count is correct (Expected: $EXPECTED_COUNT, Got: $actual_count)"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "❌ Test 1 failed: Unexpected count value (Expected: $EXPECTED_COUNT, Got: $actual_count)"
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

##############################################################################
# GET /str/areas - List areas tests
##############################################################################

echo "════════════════════════════════════════════"
echo "Testing GET /str/areas (list areas)"
echo "════════════════════════════════════════════"
echo

# Test 2: GET all areas
echo "Test 2: GET all areas"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

if [ -n "$BEARER_TOKEN" ]; then
    response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/areas")
else
    response=$(curl -s -w "\n%{http_code}" "${BACKEND_BASE_URL}/api/${API_VERSION}/str/areas")
fi

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')

echo "Response (first 500 chars): ${body:0:500}..."
echo "HTTP Status: $http_code"
echo

if [ "$http_code" -eq 200 ]; then
    # Check if response contains areas array
    if echo "$body" | grep -q '"areas"'; then
        # Extract number of areas (count occurrences of "areaId")
        area_count=$(echo "$body" | grep -o '"areaId"' | wc -l)

        if [ "$area_count" -ge 1 ]; then
            echo "✅ Test 2 passed: Retrieved $area_count area(s)"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo "❌ Test 2 failed: No areas found in response"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        echo "❌ Test 2 failed: Response does not contain 'areas' field"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
elif [ "$http_code" -eq 401 ] && [ -z "$BEARER_TOKEN" ]; then
    echo "✅ Test 2 passed: Correctly rejected unauthenticated request (401)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo "❌ Test 2 failed: Unexpected HTTP status $http_code"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo

# Test 3: GET areas with pagination (offset=0, limit=1)
echo "Test 3: GET areas with pagination (offset=0, limit=1)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Only run if authenticated
if [ -n "$BEARER_TOKEN" ]; then
    response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/areas?offset=0&limit=1")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "Response: $body"
    echo "HTTP Status: $http_code"
    echo

    if [ "$http_code" -eq 200 ]; then
        # Count number of areas in response
        area_count=$(echo "$body" | grep -o '"areaId"' | wc -l)

        if [ "$area_count" -eq 1 ]; then
            echo "✅ Test 3 passed: Retrieved exactly 1 area with limit=1"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo "❌ Test 3 failed: Expected 1 area but got $area_count"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        echo "❌ Test 3 failed: Unexpected HTTP status $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo "⏭️  Skipping Test 3 (requires authentication)"
fi

echo

# Test 4: Verify response structure
echo "Test 4: Verify response structure (areaId, competentAuthorityId, competentAuthorityName, filename, created_at)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Only run if authenticated
if [ -n "$BEARER_TOKEN" ]; then
    response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/areas?limit=1")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "Response: $body"
    echo "HTTP Status: $http_code"
    echo

    if [ "$http_code" -eq 200 ]; then
        # Check for required fields
        has_area_id=$(echo "$body" | grep -q '"areaId"' && echo "yes" || echo "no")
        has_competent_authority_id=$(echo "$body" | grep -q '"competentAuthorityId"' && echo "yes" || echo "no")
        has_competent_authority_name=$(echo "$body" | grep -q '"competentAuthorityName"' && echo "yes" || echo "no")
        has_filename=$(echo "$body" | grep -q '"filename"' && echo "yes" || echo "no")
        has_created_at=$(echo "$body" | grep -q '"createdAt"' && echo "yes" || echo "no")

        if [ "$has_area_id" = "yes" ] && [ "$has_competent_authority_id" = "yes" ] && \
           [ "$has_competent_authority_name" = "yes" ] && [ "$has_filename" = "yes" ] && \
           [ "$has_created_at" = "yes" ]; then
            echo "✅ Test 4 passed: Response contains all required fields"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo "❌ Test 4 failed: Missing required fields in response"
            echo "   - areaId: $has_area_id"
            echo "   - competentAuthorityId: $has_competent_authority_id"
            echo "   - competentAuthorityName: $has_competent_authority_name"
            echo "   - filename: $has_filename"
            echo "   - createdAt: $has_created_at"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        echo "❌ Test 4 failed: Unexpected HTTP status $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo "⏭️  Skipping Test 4 (requires authentication)"
fi

echo

##############################################################################
# GET /str/area/{areaId} - Get specific area tests
##############################################################################

echo "════════════════════════════════════════════"
echo "Testing GET /str/area/{areaId} (get area data)"
echo "════════════════════════════════════════════"
echo

# Test 5: GET area data with known areaId
echo "Test 5: GET area data with known areaId (amsterdam-area-0363)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

KNOWN_AREA_ID="amsterdam-area-0363"

if [ -n "$BEARER_TOKEN" ]; then
    # Use -i to get headers and -s for silent mode, -w to get http code
    response=$(curl -s -i -w "\n%{http_code}" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/area/${KNOWN_AREA_ID}")
else
    response=$(curl -s -i -w "\n%{http_code}" "${BACKEND_BASE_URL}/api/${API_VERSION}/str/area/${KNOWN_AREA_ID}")
fi

http_code=$(echo "$response" | tail -n1)
headers=$(echo "$response" | sed '$d')

echo "HTTP Status: $http_code"

if [ "$http_code" -eq 200 ]; then
    # Check Content-Type header
    content_type=$(echo "$headers" | grep -i "content-type:" | head -n1 | cut -d' ' -f2- | tr -d '\r')

    # Check Content-Disposition header
    content_disposition=$(echo "$headers" | grep -i "content-disposition:" | head -n1)

    echo "Content-Type: $content_type"
    echo "Content-Disposition: ${content_disposition:0:100}..."

    if echo "$content_type" | grep -q "application/octet-stream"; then
        if echo "$content_disposition" | grep -q "attachment"; then
            echo "✅ Test 5 passed: Retrieved area data with correct headers"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo "❌ Test 5 failed: Missing Content-Disposition attachment header"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        echo "❌ Test 5 failed: Expected Content-Type application/octet-stream"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
elif [ "$http_code" -eq 401 ] && [ -z "$BEARER_TOKEN" ]; then
    echo "✅ Test 5 passed: Correctly rejected unauthenticated request (401)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo "❌ Test 5 failed: Unexpected HTTP status $http_code"
    FAILED_TESTS=$((FAILED_TESTS + 1))
fi

echo

# Test 6: GET area data with another known areaId
echo "Test 6: GET area data with another known areaId (rotterdam-area-0599)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Only run if authenticated
if [ -n "$BEARER_TOKEN" ]; then
    AREA_ID_2="rotterdam-area-0599"

    response=$(curl -s -i -w "\n%{http_code}" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/area/${AREA_ID_2}")

    http_code=$(echo "$response" | tail -n1)
    headers=$(echo "$response" | sed '$d')

    echo "HTTP Status: $http_code"

    if [ "$http_code" -eq 200 ]; then
        # Check Content-Type header
        content_type=$(echo "$headers" | grep -i "content-type:" | head -n1 | cut -d' ' -f2- | tr -d '\r')

        if echo "$content_type" | grep -q "application/octet-stream"; then
            echo "✅ Test 6 passed: Retrieved area data for Rotterdam"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo "❌ Test 6 failed: Expected Content-Type application/octet-stream"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        echo "❌ Test 6 failed: Unexpected HTTP status $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo "⏭️  Skipping Test 6 (requires authentication)"
fi

echo

# Test 7: GET area data with non-existent areaId (should return 404)
echo "Test 7: GET area data with non-existent areaId (should return 404)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Only run if authenticated
if [ -n "$BEARER_TOKEN" ]; then
    NONEXISTENT_AREA_ID="nonexistent-area-99999"

    response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/area/${NONEXISTENT_AREA_ID}")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    echo "Response: $body"
    echo "HTTP Status: $http_code"
    echo

    if [ "$http_code" -eq 404 ]; then
        echo "✅ Test 7 passed: Correctly returned 404 for non-existent area"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo "❌ Test 7 failed: Expected 404 but got $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo "⏭️  Skipping Test 7 (requires authentication)"
fi

echo

# Test 8: Verify Content-Disposition filename
echo "Test 8: Verify Content-Disposition contains filename"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

# Only run if authenticated
if [ -n "$BEARER_TOKEN" ]; then
    AREA_ID_3="denhaag-area-0518"

    response=$(curl -s -i -w "\n%{http_code}" \
        -H "Authorization: Bearer ${BEARER_TOKEN}" \
        "${BACKEND_BASE_URL}/api/${API_VERSION}/str/area/${AREA_ID_3}")

    http_code=$(echo "$response" | tail -n1)
    headers=$(echo "$response" | sed '$d')

    echo "HTTP Status: $http_code"

    if [ "$http_code" -eq 200 ]; then
        # Check Content-Disposition header for filename
        content_disposition=$(echo "$headers" | grep -i "content-disposition:" | head -n1)

        echo "Content-Disposition: $content_disposition"

        if echo "$content_disposition" | grep -q "filename="; then
            echo "✅ Test 8 passed: Content-Disposition contains filename"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo "❌ Test 8 failed: Content-Disposition does not contain filename"
            FAILED_TESTS=$((FAILED_TESTS + 1))
        fi
    else
        echo "❌ Test 8 failed: Unexpected HTTP status $http_code"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
else
    echo "⏭️  Skipping Test 8 (requires authentication)"
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
    echo "✅ All STR areas endpoint tests passed!"
    exit 0
else
    echo "❌ Some STR areas endpoint tests failed!"
    exit 1
fi
