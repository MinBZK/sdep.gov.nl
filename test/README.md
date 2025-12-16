# Integration Test Scripts

This directory contains shell scripts for integration testing the SDEP (Single Digital Entry Point) API endpoints. These tests verify API functionality, authentication, authorization, and security compliance.

## Prerequisites

### Environment Variables

All test scripts require:
- `BACKEND_BASE_URL` - Base URL of the API server (e.g., `http://localhost:8000`)
- `API_VERSION` - API version (optional, defaults to `v0`)

Authentication tests also require:
- `CLIENT_ID` - OAuth2 client ID for authentication
- `CLIENT_SECRET` - OAuth2 client secret for authentication

Alternatively, you can directly provide:
- `BEARER_TOKEN` - Pre-generated JWT bearer token

See also [../Makefile](../Makefile).

### Running Tests

See [../Makefile](../Makefile).

## Test Scripts Overview

### 🔐 Authentication & Authorization Tests

#### `auth_client.sh`
**Purpose:** Utility script to authenticate and save bearer token

**What it does:**
- Performs OAuth2 client credentials flow
- Requests access token from `/api/v0/auth/token`
- Saves token to `./tmp/.bearer_token` for use by other scripts
- Used as a prerequisite for authenticated endpoint tests

**Usage:**
```bash
CLIENT_ID=sdep-str-01 CLIENT_SECRET=sdep-str-01 \
  BACKEND_BASE_URL=http://localhost:8000 \
  ./auth_client.sh
```

#### `auth_credentials.sh`
**Purpose:** Test authentication with various credential scenarios

**What it tests:**
- Valid credentials authentication
- Invalid credentials (wrong client_id/secret)
- Missing credentials
- Malformed requests

#### `auth_headers.sh`
**Purpose:** Verify security headers compliance

**What it tests:**
- XSS protection headers
- Content Security Policy (CSP)
- OWASP security header compliance
- Output encoding verification
- Prevents clickjacking attacks
- Secure cookie settings

**Expected headers:**
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Content-Security-Policy`
- `Strict-Transport-Security` (HSTS)

#### `auth_unauthorized.sh`
**Purpose:** Test unauthorized access scenarios

**What it tests:**
- Missing bearer token
- Invalid/expired bearer token
- Malformed Authorization header
- Token with insufficient permissions

**Expected:** All tests should return `401 Unauthorized` or `403 Forbidden`

---

### 🏥 Health Check Tests

#### `health_ping.sh`
**Purpose:** Basic API availability test

**What it tests:**
- API server is running and responding
- Health endpoint accessibility
- Response time and format

**Endpoint:** `GET /api/health`

**Expected:** `200 OK` with health status

---

### 🏢 Competent Authority (CA) Endpoints

#### `ca_areas.sh`
**Purpose:** Test area submission for competent authorities

**What it tests:**
- `POST /ca/areas` - Submit area definitions with shapefile data
- **Validation error handling** (Layer 1: Pydantic, Layer 2: Business Logic)
- Partial success/failure scenarios (some areas succeed, others fail)
- Detailed error responses with field-level validation
- Batch area creation (1-100 areas per request)
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

#### `ca_activities.sh`
**Purpose:** Test activity query for competent authorities

**What it tests:**
- `GET /ca/activities` - Query activities in CA jurisdiction
- Filtering by area, date range, status
- Pagination support
- Authorization checks (CA can only see their own jurisdiction)

**Authentication:** Requires CA client credentials with `sdep_ca` role

---

### 🏠 Short-Term Rental (STR) Platform Endpoints

#### `str_areas.sh`
**Purpose:** Test area lookup for STR platforms

**What it tests:**
- `GET /str/areas` - Query available areas
- Area search by location/coordinates
- Competent authority information retrieval
- Response format validation

**Authentication:** Requires STR platform credentials with `sdep_str` role

#### `str_activities.sh`
**Purpose:** Test activity submission for STR platforms

**What it tests:**
- `POST /str/activities` - Submit rental activities
- **Validation error handling** (Layer 1: Pydantic, Layer 2: Business Logic)
- Partial success/failure scenarios (some activities succeed, others fail)
- Detailed error responses with field-level validation
- Batch activity creation (1-100 activities per request)
- Duplicate detection
- Required field validation (address, temporal, registration)

**Authentication:** Requires STR platform credentials with `sdep_str` and `sdep_write` roles

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

## Test Client Credentials

Default test clients (defined in `keycloak/clients.yaml`):

### Competent Authority (CA) Client
- **Client ID:** `sdep-ca-0363`
- **Client Secret:** `sdep-ca-0363`
- **Roles:** `sdep_ca`, `sdep_write`, `sdep_read`
- **Can access:** CA endpoints for area 0363 (Amsterdam)

### STR Platform Client
- **Client ID:** `sdep-str-01`
- **Client Secret:** `sdep-str-01`
- **Roles:** `sdep_str`, `sdep_write`, `sdep_read`
- **Can access:** STR platform endpoints

---

## Token Storage

- Tokens are saved to `./tmp/.bearer_token` by `auth-client.sh`
- Other scripts automatically load tokens from this file
- Token location is configurable via scripts

---

## Exit Codes

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
- Ensure backend server is running: `make up` or `docker-compose up`
- Check `BACKEND_BASE_URL` points to correct host/port
