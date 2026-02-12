<h1>Integration Test Scripts</h1>

This directory contains shell scripts for integration testing the SDEP (Single Digital Entry Point) API endpoints. These tests verify API functionality, authentication, authorization, and security compliance.

## Running Tests

See [../Makefile](../Makefile).

## Authentication & authorization tests

### `auth_client.sh`
**Purpose:** Utility script to authenticate and save bearer token

**What it does:**
- Performs OAuth2 client credentials flow
- Requests access token from `/api/v0/auth/token`
- Saves token to `./tmp/.bearer_token` for use by other scripts
- Used as a prerequisite for authenticated endpoint tests

### `auth_credentials.sh`
**Purpose:** Test OAuth2 token acquisition for both STR and CA clients

**What it tests:**
- STR platform client credentials authentication
- CA (Competent Authority) client credentials authentication
- JWT token acquisition and decoding
- Token payload inspection

### `auth_headers.sh`
**Purpose:** Verify security headers compliance across multiple endpoints

**Endpoints tested:**
- `/` - Root endpoint
- `/api/health` - Health check
- `/api/v0/ping` - Ping endpoint
- `/api/v0/openapi.json` - OpenAPI specification

**What it tests:**
- XSS protection headers
- Content Security Policy (CSP)
- OWASP security header compliance
- Output encoding verification
- Prevents clickjacking attacks
- Secure cookie settings

### `auth_unauthorized.sh`
**Purpose:** Verify all secured endpoints properly reject unauthenticated requests

**Endpoints tested:**
- `GET /api/v0/ping`
- `GET /api/v0/str/areas`
- `GET /api/v0/str/areas/count`
- `GET /api/v0/str/areas/{areaId}`
- `POST /api/v0/str/activities`
- `GET /api/v0/ca/activities`
- `GET /api/v0/ca/activities/count`
- `POST /api/v0/ca/areas`

**What it tests:**
- All secured endpoints return `401 Unauthorized` without authentication token
- Public endpoints (like `/api/health`) are excluded from this test

---

## Healthcheck tests

### `health_ping.sh`
**Purpose:** Basic API availability test

**What it tests:**
- API server is running and responding
- Ping endpoint accessibility
- Response time and format
- Authenticated and unauthenticated access

---

## Competent Authority (CA) tests

### `ca_areas.sh`
**Purpose:** Test area submission for competent authorities

**What it tests:**
- `POST /ca/areas` - Submit area definitions with shapefile data
- **Validation error handling** (Layer 1: Pydantic, Layer 2: Business Logic)
- Partial success/failure scenarios (some areas succeed, others fail)
- Detailed error responses with field-level validation
- Bulk area creation (1-100 areas per request)
- Duplicate detection
- Required field validation (filename, filedata)

**Authentication:** Requires CA client credentials with `sdep_ca` and `sdep_write` roles

**Payload:** Area definitions with base64-encoded shapefile data

**Key Features Tested:**
- ✅ Valid area submission
- ✅ Invalid filedata (missing, corrupted)
- ✅ Missing required fields
- ✅ Empty area lists
- ✅ Duplicate area detection
- ✅ Combined Pydantic + business logic validation errors

**Validation Behavior:**
- ✅ Pydantic validation errors collected (Layer 1)
- ✅ Business logic validation continues (Layer 2)
- ✅ All errors returned together with detailed field paths
- ✅ Partial success supported (some areas succeed, others fail)

**HTTP Status Codes:**
- `201 Created` - All areas succeeded
- `200 OK` - Partial success (some succeeded, some failed)
- `422 Unprocessable Entity` - All areas failed

### `ca_activities.sh`
**Purpose:** Comprehensive testing of activity query endpoints for competent authorities

**What it tests:**
- **Test 1:** Count activities (`GET /ca/activities/count`)
- **Test 2:** Get all activities
- **Test 3:** Pagination (offset=0, limit=1)
- **Test 4:** Verify response structure (activityId, activityName, platformId, platformName, url, registrationNumber, address, temporal, areaId)
- **Test 5:** GET specific activity by URL filter
- **Test 6:** GET activities filtered by areaId
- **Test 7:** GET with non-existent areaId (should return empty or 404)
- **Test 8:** Verify pagination consistency (offset and limit)

**Endpoints:**
- `GET /ca/activities/count`
- `GET /ca/activities`
- `GET /ca/activities?url={url}`
- `GET /ca/activities?areaId={areaId}`
- `GET /ca/activities?offset={offset}&limit={limit}`

---

## Short-Term Rental (STR) Platform tests

### `str_areas.sh`
**Purpose:** Comprehensive testing of area lookup endpoints for STR platforms

**What it tests:**
- **Test 1:** Count areas (`GET /str/areas/count`) - expects minimal 28 areas
- **Test 2:** GET all areas and extract area IDs for subsequent tests
- **Test 3:** GET areas with pagination (offset=0, limit=1)
- **Test 4:** Verify response structure (areaId, competentAuthorityId, competentAuthorityName, filename, createdAt)
- **Test 5:** GET specific area by areaId (returns shapefile as `application/octet-stream`)
- **Test 6:** GET another area by areaId
- **Test 7:** GET non-existent area (should return 404)
- **Test 8:** Verify Content-Disposition header contains filename

**Endpoints:**
- `GET /str/areas/count`
- `GET /str/areas`
- `GET /str/areas?offset={offset}&limit={limit}`
- `GET /str/areas/{areaId}` - Downloads shapefile

**Response Formats:**
- List endpoints: `application/json`
- Download endpoint: `application/octet-stream` with `Content-Disposition: attachment`

### `str_activities.sh`
**Purpose:** Test activity submission for STR platforms

**What it tests:**
- `POST /str/activities` - Submit rental activities
- **Validation error handling** (Layer 1: Pydantic, Layer 2: Business Logic)
- Partial success/failure scenarios (some activities succeed, others fail)
- Detailed error responses with field-level validation
- Bulk activity creation (1-100 activities per request)
- Duplicate detection
- Required field validation (address, temporal, registration)

**Key Features Tested:**
- ✅ Valid activity submission
- ✅ Invalid postal codes (too long, contains spaces, special characters)
- ✅ Invalid temporal data (end before start, year before 2025)
- ✅ Invalid field types (string where int expected, etc.)
- ✅ Missing required fields
- ✅ Empty activity lists
- ✅ Duplicate activity detection
- ✅ Combined Pydantic + business logic validation errors

**Validation Behavior:**
- ✅ Pydantic validation errors collected (Layer 1)
- ✅ Business logic validation continues (Layer 2)
- ✅ All errors returned together with detailed field paths
- ✅ Partial success supported (some activities succeed, others fail)

This allows clients to see all validation issues at once instead of fixing one error at a time.

---

## Configuration

### Credentials

Default test clients are defined in `keycloak/clients.yaml`:

**Competent Authority (CA)**
- **Client ID:** `sdep-ca0363`
- **Client Secret:** `sdep-ca0363`
- **Roles:** `sdep_ca`, `sdep_write`, `sdep_read`
- **Can access:** CA endpoints for area 0363 (Amsterdam)

**STR Platform**
- **Client ID:** `sdep-test-str01`
- **Client Secret:** `sdep-test-str01`
- **Roles:** `sdep_str`, `sdep_write`, `sdep_read`
- **Can access:** STR platform endpoints

---

### Bearer tokens

- Tokens are saved to `./tmp/.bearer_token` by `auth-client.sh`
- Other scripts automatically load tokens from this file
- Token location is configurable via scripts

---

### Exit Codes

All test scripts follow standard Unix exit codes:
- `0` - All tests passed
- `1` - Test failed or error occurred

---

## Troubleshooting

### Common Issues

**"BACKEND_BASE_URL environment variable is not set"**
- Solution: `export BACKEND_BASE_URL="http://localhost:8000"`

**"401 Unauthorized"**
- Check if token is expired
- Re-run `auth-client.sh` to get a fresh token
- Verify client credentials are correct

**"403 Forbidden"**
- Client lacks required roles
- Verify client has appropriate permissions in Keycloak

**Connection refused**
- Ensure backend server is running: `make up`
- Check `BACKEND_BASE_URL` points to correct host/port
- Restart everything: `make restart`
