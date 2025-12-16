# ID Pattern Documentation

## Overview

The SDEP API uses a **dual ID pattern** that separates technical database identifiers from functional business identifiers. This design provides stable references while allowing optional business-meaningful identifiers.

## Dual ID Pattern

### Technical ID
- **Type**: String (20-character UUID)
- **Generation**: `uuid.uuid4().hex[:20]` - first 20 characters of UUID4 hex
- **Purpose**: Database primary key and stable references
- **Visibility**: Returned in GET responses, used in GET `/{id}` endpoints
- **Format**: Lowercase hexadecimal `^[a-f0-9]{20}$`
- **Example**: `"a1b2c3d4e5f6a7b8c9d0"`

### Functional ID
- **Type**: String (lowercase alphanumeric with dashes)
- **Purpose**: Business identifier, optional in POST requests
- **Nullable**: Can be null if not provided by submitter
- **Example**: `"amsterdam-area-0363"` or `null`

## Endpoints and ID Usage

### POST /ca/areas
**Request:**
```json
{
  "competentAuthorityAreaId": "amsterdam-area-0363",  // Optional functional ID
  "filename": "Amsterdam.zip",
  "filedata": "base64..."
}
```

- `competentAuthorityAreaId` (optional): Functional business ID
- If not provided → remains `null` (not auto-generated)
- Submitter ID comes from JWT token (authenticated client)

**Response:**
```json
{
  "areaId": "a1b2c3d4e5f6a7b8c9d0",                    // Technical ID (UUID string)
  "competentAuthorityId": "sdep-ca-0363",              // Functional submitter ID
  "competentAuthorityName": "Gemeente Amsterdam",       // Submitter name
  "competentAuthorityAreaId": "amsterdam-area-0363",   // Functional area ID (or null)
  "filename": "Amsterdam.zip",
  "createdAt": "2025-01-15T10:30:00Z"
}
```

**Pattern**: Response includes BOTH technical and functional IDs

### POST /str/activities
**Request:**
```json
{
  "platformActivityId": "activity-001",              // Optional functional ID
  "areaId": "a1b2c3d4e5f6a7b8c9d0",                 // REQUIRED: Technical area ID (UUID string)
  "url": "http://example.com/listing",
  "address": { ... },
  "registrationNumber": "REG123",
  "temporal": { ... }
}
```

**Critical Points:**
- `areaId`: **Technical ID (UUID string)** - references existing Area by primary key
- `platformActivityId`: Optional functional ID (remains null if not provided)
- Platform info comes from JWT token (no need to specify)

**Pattern**: POST uses functional IDs for entity itself, technical IDs for foreign key references

### GET /str/areas
**Response:**
```json
{
  "areas": [
    {
      "areaId": "a1b2c3d4e5f6a7b8c9d0",                 // Technical ID (UUID)
      "competentAuthorityId": "sdep-ca-0363",          // Functional submitter ID
      "competentAuthorityName": "Gemeente Amsterdam",   // Submitter name
      "competentAuthorityAreaId": "amsterdam-area-0363", // Functional area ID
      "filename": "Amsterdam.zip",
      "createdAt": "2025-01-15T10:30:00Z"
    }
  ]
}
```

**Pattern**: Returns technical ID + origin (functional IDs + names)

### GET /str/areas/{areaId}
**Path Parameter:**
- `areaId`: Technical ID (20-character UUID string)
- Example: `GET /str/areas/a1b2c3d4e5f6a7b8c9d0`

**Response**: Binary filedata download

**Pattern**: Direct resource retrieval uses technical ID

## Versioning

Versioning is supported by creating new records with the same functional ID but different timestamps:

### Example: Area Versioning
```json
// Version 1 - submitted at 10:00
POST /ca/areas
{
  "competentAuthorityAreaId": "amsterdam-area-0363",
  "filename": "Amsterdam-v1.zip",
  "filedata": "..."
}
// Creates: areaId="abc123...", created_at=2025-01-15T10:00:00Z

// Version 2 - submitted at 11:00 (correction/update)
POST /ca/areas
{
  "competentAuthorityAreaId": "amsterdam-area-0363",  // Same functional ID
  "filename": "Amsterdam-v2.zip",
  "filedata": "..."
}
// Creates: areaId="def456...", created_at=2025-01-15T11:00:00Z

// Both versions exist with different technical IDs and timestamps
```

**Use Cases:**
- Corrections to previously submitted data
- Temporal validity (different versions valid at different times)
- Audit trail (all versions preserved)

**Note**: Versioning relies on application logic, not database constraints. The combination of (submitter + functional_id + timestamp) provides logical uniqueness, but database allows duplicates.

## Migration from Old Pattern

### Breaking Changes

**Activity Schema:**
- `areaId`: Changed from `int` (old) to `string` (UUID)
- Type in API requests/responses: Integer → String

**Before (OLD):**
```json
{
  "areaId": 1,  // Integer
  ...
}
```

**After (NEW):**
```json
{
  "areaId": "a1b2c3d4e5f6a7b8c9d0",  // UUID string
  ...
}
```

### Migration Steps

1. **Populate areas first**: Use POST /ca/areas to create all areas
2. **Capture technical IDs**: From POST /ca/areas responses, save `areaId` values (UUID strings)
3. **Reference in activities**: Use captured technical IDs in POST /str/activities

### Example Migration Workflow

```bash
# Step 1: Create area
response=$(curl -X POST /ca/areas \
  -d '{"competentAuthorityAreaId": "amsterdam-area-0363", ...}')
AREA_ID=$(echo "$response" | jq -r '.areaId')  # Extract UUID string

# Step 2: Use UUID string in activity
curl -X POST /str/activities \
  -d "{\"areaId\": \"$AREA_ID\", ...}"  # Use UUID string
```

## Design Rationale

### Why Dual IDs?

**Technical IDs (UUID strings):**
- Globally unique without database coordination
- Stable references for relationships
- No auto-increment race conditions
- Suitable for distributed systems

**Functional IDs (strings):**
- Meaningful to business users ("amsterdam-area-0363")
- Optional (flexibility for clients who don't have business IDs)
- Support versioning when combined with timestamp

### Why Technical IDs for Foreign Key References?

**Problem**: Using functional IDs for foreign keys creates ambiguity
```
Activity references areaId="amsterdam-area-0363"
→ Which version? (multiple versions may exist with different timestamps)
```

**Solution**: Use technical ID (unambiguous reference)
```
Activity references areaId="a1b2c3d4e5f6a7b8c9d0"
→ Exact version specified
```

## Summary

| Aspect          | Technical ID                    | Functional ID            |
| --------------- | ------------------------------- | ------------------------ |
| Type            | String (20-char UUID)           | String                   |
| Format          | `^[a-f0-9]{20}$`                | Alphanumeric with dashes |
| Required        | Always (auto-generated)         | Optional                 |
| Nullable        | No                              | Yes                      |
| Purpose         | DB primary key, stable ref      | Business key             |
| In POST request | For foreign key refs only       | For entity itself        |
| In GET response | Always included                 | Always included          |
| Uniqueness      | Globally unique                 | Not enforced             |
| Versioning      | New ID per version              | Same ID across versions  |

**Key Principles**:
- **POST**: Functional IDs are optional (entity), technical IDs are required (foreign key references)
- **GET**: Both IDs returned (technical for retrieval, functional for business context)
- **Versioning**: Enabled by application logic (submitter + functional_id + timestamp pattern)
- **No Auto-generation**: Functional IDs remain `null` if not provided (not auto-generated)
