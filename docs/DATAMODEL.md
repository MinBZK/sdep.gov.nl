# Data Model Documentation

![](./Datamodel.svg)

## Purpose

This datamodel supports the Single Digital Entry Point (SDEP) for short-term rental regulation. It enables:
- **Platforms** to submit rental activities to competent authorities
- **Competent Authorities** to define geographic areas and receive activity data

## Core Entities

### Platform
**Purpose:** Delivers rental activities to competent authorities

**Attributes:**
- `platformId` (string): Functional ID, auto-provisioned on first POST, mandatory, unique
- `platformName` (string): Optional display name (e.g., "Example platform")
- `activities`: References to Activity entities

**Unique Constraint:** `(platformId, createdAt)`

**API Operations:**
- POST `/str/activities` - Submit activities (bulk, 1-1000 records)
- GET `/str/areas` - Retrieve available geographic areas

---

### CompetentAuthority
**Purpose:** Regulates short-term rental in specific geographic areas

**Attributes:**
- `competentAuthorityId` (string): Functional ID, auto-provisioned on first POST, mandatory, unique
- `competentAuthorityName` (string): Optional display name (e.g., "Gemeente Amsterdam")
- `areas`: References to Area entities

**Unique Constraint:** `(competentAuthorityId, createdAt)`

**API Operations:**
- POST `/ca/areas` - Submit geographic areas (bulk, 1-1000 records)
- GET `/ca/activities` - Retrieve submitted activities for their areas

---

### Activity
**Purpose:** Represents an actual rental activity submitted by a platform

**Attributes:**
- `activityId` (string): Functional ID, optional (auto-generated if not supplied)
- `activityName` (string): Optional human-readable name (max 128 chars, e.g., "Summer rental")
- `platform`: Reference to Platform entity
- `area`: Reference to Area entity (required)
- `url` (string): Advertisement URL (e.g., "http://example.com/my-advertisement")
- `address`: Reference to Address composite (required)
- `registrationNumber` (string): Registration number (mandatory)
- `numberOfGuests` (int): Number of guests (min: 1, max: 1024)
- `countryOfGuests` (array of string): ISO 3166-1 alpha-3 country codes (min: 1, max: 1024)
- `temporal`: Reference to Temporal composite (required)

**Unique Constraint:** `(activityId, createdAt)`

**Notes:**
- Same `activityId` can be resubmitted to create new versions with different timestamps
- Each activity must reference an existing area
- Processed independently with partial success/failure support

---

### Area
**Purpose:** Defines a geographic region for short-term rental regulation

**Attributes:**
- `areaId` (string): Functional ID, optional (auto-generated if not supplied)
- `areaName` (string): Optional human-readable name (e.g., "Amsterdam-Noord")
- `filename` (string): Shapefile name (mandatory, e.g., "Amsterdam.zip")
- `filedata` (largeBinary): ESRI shapefile content (mandatory, max 1MiB, typically .zip format)

**Unique Constraint:** `(areaId, createdAt)`

**Notes:**
- Same `areaId` can be resubmitted to create new versions with different timestamps
- Shapefiles define geographic boundaries for regulatory purposes
- Retrieved as binary octet-stream via GET `/str/areas/{areaId}`

---

### Address (Composite)
**Purpose:** Structured address information for rental activities

**Attributes:**
- `street` (string): Street name (mandatory, e.g., "Turfmarkt")
- `number` (int): House number (mandatory, e.g., 147)
- `letter` (string): House letter (optional)
- `addition` (string): House addition (optional)
- `postalCode` (string): Postal code (mandatory, e.g., "2500EA")
- `city` (string): City name (mandatory, e.g., "Den Haag")

---

### Temporal (Composite)
**Purpose:** Time period information for rental activities

**Attributes:**
- `startDatetime` (datetime): Start date/time (mandatory, year must be >= 2025)
- `endDatetime` (datetime): End date/time (mandatory)

**Constraint:** `startDatetime < endDatetime`

---

## Key Patterns

### ID Management
- **Functional IDs:** Client-provided business identifiers (optional) or auto-generated RFC 9562 UUIDs
- **Auto-provisioning:** Platform and CompetentAuthority IDs are auto-generated on first POST

### Versioning
- Entities use `(functionalId, createdAt)` as unique constraint
- Same functional ID can be resubmitted with new timestamp for versioning
- Enables historical tracking and updates without losing previous versions

### Bulk Processing
- All POST endpoints support bulk operations (1-1000 records per request)
- Independent processing with savepoints (nested transactions)
- Partial success/failure support - some records can succeed while others fail
- Response includes detailed success/failure breakdown with indices

### Authorization
- **Platforms:** Require `sdep_str` role
  - `sdep_write` for POST operations (submitting activities)
  - `sdep_read` for GET operations (reading areas)
- **Competent Authorities:** Require `sdep_ca` role
  - `sdep_write` for POST operations (submitting areas)
  - `sdep_read` for GET operations (reading activities)

## Entity Relationships

```
Platform (1) ----< (N) Activity (N) >---- (1) Area (N) >---- (1) CompetentAuthority
                           |
                           +---- (1) Address (composite)
                           +---- (1) Temporal (composite)
```

- **Platform** submits many **Activities**
- **Activity** references one **Area** (geographic location)
- **Activity** embeds one **Address** (rental location details)
- **Activity** embeds one **Temporal** (rental time period)
- **CompetentAuthority** defines many **Areas**
- Activities are routed to CompetentAuthorities based on the referenced Area
