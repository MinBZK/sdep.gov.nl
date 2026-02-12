<h1>Architecture</h1>

This document provides an overview of the SDEP (Single Digital Entry Point) project structure, technology stack, and key components.

- [Overview](#overview)
- [Technology Stack](#technology-stack)
  - [Backend](#backend)
  - [Infrastructure](#infrastructure)
  - [Development Tools](#development-tools)
- [Directory Structure](#directory-structure)
- [Backend Architecture](#backend-architecture)
  - [API Layer (`app/api/`)](#api-layer-appapi)
  - [Schemas Layer (`app/schemas/`)](#schemas-layer-appschemas)
  - [Service Layer (`app/services/`)](#service-layer-appservices)
  - [CRUD Layer (`app/crud/`)](#crud-layer-appcrud)
  - [Models Layer (`app/models/`)](#models-layer-appmodels)
- [Key Endpoints](#key-endpoints)
  - [Authentication](#authentication)
  - [Competent Authority (CA) - Requires `sdep_ca` role](#competent-authority-ca-requires-sdep_ca-role)
  - [Short-Term Rental Platform (STR) - Requires `sdep_str` role](#short-term-rental-platform-str-requires-sdep_str-role)
  - [Health](#health)
- [Development Workflow](#development-workflow)
- [Testing Strategy](#testing-strategy)
  - [Unit Tests (`backend/tests/`)](#unit-tests-backendtests)
  - [Integration Tests (`tests/`)](#integration-tests-tests)
  - [Test Coverage](#test-coverage)
- [Key Configuration Files](#key-configuration-files)
- [Authentication \& Authorization](#authentication-authorization)


## Overview

SDEP is a FastAPI-based REST API that enables:
- Competent Authorities (CA) to register regulated areas with geospatial data
- Short-Term Rental platforms (STR) to query regulated areas and submit rental activities
- Competent Authorities (CA) to query rental activities
- Compliance with EU Regulation 2024/1028

**Production:** https://sdep.gov.nl/api/v0/docs

## Technology Stack

### Backend
- **Python:** 3.13+
- **Framework:** FastAPI 0.115+
- **ORM:** SQLAlchemy 2.0+ (async)
- **Migrations:** Alembic
- **Validation:** Pydantic 2.10+
- **Authentication:** OAuth2 Client Credentials via Keycloak
- **Server:** Uvicorn

### Infrastructure
- **Container Platform:** Docker + Docker Compose
- **Identity Provider:** Keycloak (OAuth2/OIDC)
- **Database:** PostgreSQL 15+
- **Package Manager:** uv (Python)

### Development Tools
- **Linting:** Ruff
- **Type Checking:** Pyright
- **Testing:** pytest (with pytest-asyncio, pytest-xdist for parallel execution)
- **Pre-commit:** Hooks for code quality
- **CI/CD:** GitLab CI or otherwise (out of scope for this project)

## Directory Structure

```
sdep-app/
├── backend/                                # Python FastAPI application
│   ├── app/                                # Application code
│   │   ├── api/                            # API layer (routers, endpoints)
│   │   │   ├── common/                     # Shared API components
│   │   │   │   ├── routers/                # API routers
│   │   │   │   │   ├── auth.py             # Authentication router
│   │   │   │   │   ├── ca_activities.py    # CA activity endpoints
│   │   │   │   │   ├── ca_areas.py         # CA area endpoints
│   │   │   │   │   ├── health.py           # Health check router
│   │   │   │   │   ├── ping.py             # Ping endpoint
│   │   │   │   │   ├── str_activities.py   # STR activity endpoints
│   │   │   │   │   └── str_areas.py        # STR area endpoints
│   │   │   │   ├── exception_handlers.py
│   │   │   │   ├── openapi.py
│   │   │   │   └── security.py
│   │   │   └── v0/                         # API version 0
│   │   │       ├── main.py                 # API v0 entry point
│   │   │       └── security.py             # v0 security configuration
│   │   ├── crud/                           # Database operations (CRUD)
│   │   │   ├── activity.py
│   │   │   ├── area.py
│   │   │   ├── competent_authority.py
│   │   │   └── platform.py
│   │   ├── db/                             # Database configuration
│   │   │   └── config.py                   # Database session management
│   │   ├── exceptions/                     # Custom exceptions
│   │   │   ├── auth.py                     # Authentication exceptions
│   │   │   ├── base.py                     # Base exception classes
│   │   │   ├── business.py                 # Business logic exceptions
│   │   │   ├── handlers.py                 # Exception handlers
│   │   │   └── validation.py               # Validation exceptions
│   │   ├── models/                         # SQLAlchemy ORM models
│   │   │   ├── activity.py
│   │   │   ├── address.py
│   │   │   ├── area.py
│   │   │   ├── competent_authority.py
│   │   │   ├── platform.py
│   │   │   └── temporal.py
│   │   ├── schemas/                        # Pydantic schemas (request/response)
│   │   │   ├── activity.py
│   │   │   ├── area.py
│   │   │   ├── auth.py
│   │   │   ├── error.py
│   │   │   ├── health.py
│   │   │   └── validation.py
│   │   ├── security/                       # Security utilities
│   │   │   ├── bearer.py                   # Bearer token handling
│   │   │   └── headers.py                  # Security headers
│   │   ├── services/                       # Business logic layer
│   │   │   ├── activity.py
│   │   │   └── area.py
│   │   ├── config.py                       # Application configuration
│   │   └── main.py                         # Application entry point
│   ├── alembic/                            # Database migrations
│   │   ├── env.py                          # Alembic environment config
│   │   └── versions/                       # Migration scripts
│   │       └── 001_initial.py              # Initial migration
│   ├── tests/                              # Unit tests (mirrors app/ structure)
│   │   ├── api/                            # API layer tests
│   │   ├── crud/                           # CRUD layer tests
│   │   ├── fixtures/                       # Test fixtures and factories
│   │   ├── security/                       # Security tests
│   │   ├── services/                       # Service layer tests
│   │   └── conftest.py                     # pytest configuration
│   ├── alembic.ini                         # Alembic configuration
│   ├── Dockerfile                          # Backend container image
│   ├── Makefile                            # Backend-specific make targets
│   ├── pyproject.toml                      # Python project configuration (uv)
│   └── uv.lock                             # Locked dependencies
│
├── tests/                                  # Integration tests (shell scripts)
│   ├── auth_client.sh                      # OAuth2 token acquisition utility
│   ├── auth_credentials.sh                 # Test client credentials flow
│   ├── auth_headers.sh                     # Security headers compliance
│   ├── auth_unauthorized.sh                # Test unauthorized access rejection
│   ├── ca_activities.sh                    # Test CA activity endpoints
│   ├── ca_areas.sh                         # Test CA area submission
│   ├── health_ping.sh                      # Health check tests
│   ├── str_activities.sh                   # Test STR activity submission
│   ├── str_areas.sh                        # Test STR area query endpoints
│   └── README.md                           # Test documentation
│
├── keycloak/                               # Keycloak configuration
│   ├── add-realm-admin.sh                  # Create realm admin user
│   ├── add-realm-clients.sh                # Configure OAuth2 clients
│   ├── add-realm-roles.sh                  # Configure roles
│   ├── add-realm.sh                        # Initialize realm
│   ├── clients.yaml                        # Client definitions (CA, STR)
│   ├── roles.yaml                          # Role definitions
│   └── wait.sh                             # Wait for Keycloak startup
│
├── postgres/                               # PostgreSQL initialization
│   ├── clean-app.sql                       # Database cleanup
│   ├── init-keycloak.sql                   # Keycloak database setup
│   └── init-app.sql                        # SDEP database setup
│
├── test-data/                              # Test data for integration tests
│   ├── 01-competent-authority.sql          # Competent authority fixtures
│   ├── 02-area-generated.sql               # Generated area data
│   └── generate-area-sql.sh                # Area data generator script
│
├── docs/                                   # Documentation
│   ├── APPROACH.md                         # Development approach
│   ├── ARCHITECTURE.md                     # Architecture overview (this file)
│   ├── DATAMODEL.md                        # Data model documentation
│   ├── DATAMODEL.drawio                    # Data model diagram (draw.io)
│   ├── DATAMODEL.svg                       # Data model diagram (SVG)
│   ├── DESIGN.md                           # Design decisions log
│   └── LIMITATIONS.md                      # Known limitations
│
├── .claude/                                # Claude Code configuration
│   └── commands/                           # Custom slash commands
│
├── .env                                    # Environment variables
├── .gitignore                              # Git ignore rules
├── .gitlab-ci.yml                          # GitLab CI/CD configuration
├── AGENTS.md                               # Claude agent configuration
├── CLAUDE.md                               # Claude Code instructions
├── docker-compose.yml                      # Multi-container orchestration
├── LICENSE.md                              # EUPL License
├── Makefile                                # Root-level make targets
└── README.md                               # Quick start guide
```

## Backend Architecture

The backend follows a **layered architecture** pattern:

### API Layer (`app/api/`)
- HTTP request/response handling
- Route definitions and parameter validation
- Authentication/authorization enforcement
- Manual transaction boundaries (per HTTP request)
- Commits transactions if at least one record succeeds

### Schemas Layer (`app/schemas/`)
- Pydantic models for request/response validation
- Data serialization/deserialization
- Validation (Layer 1: type/format validation)

### Service Layer (`app/services/`)
- Business logic implementation
- Validation (Layer 2: business rules)
- Uses nested transactions (savepoints) for independent record processing
- Collects validation and processing errors
- Returns partial success/failure responses

### CRUD Layer (`app/crud/`)
- Database operations (Create, Read, Update, Delete)
- Data access abstraction
- SQLAlchemy query construction
- Uses flush (not commit) - defers transaction control to upper layers

### Models Layer (`app/models/`)
- SQLAlchemy ORM models
- Database table definitions
- Relationships and constraints

## Key Endpoints

### Authentication
- `POST /api/v0/auth/token` - OAuth2 token endpoint

### Competent Authority (CA) - Requires `sdep_ca` role
- `POST /api/v0/ca/areas` - Submit regulated areas (bulk, 1-1000 areas)
- `GET /api/v0/ca/activities` - Query rental activities
- `GET /api/v0/ca/activities/count` - Count activities

### Short-Term Rental Platform (STR) - Requires `sdep_str` role
- `GET /api/v0/str/areas` - List regulated areas
- `GET /api/v0/str/areas/count` - Count areas
- `GET /api/v0/str/areas/{areaId}` - Download shapefile for area
- `POST /api/v0/str/activities` - Submit rental activities (bulk, 1-1000 activities)

### Health
- `GET /api/health` - Health check (unauthenticated)
- `GET /api/v0/ping` - Ping endpoint (authenticated)

## Development Workflow

See makefile help
```
make
```

## Testing Strategy

### Unit Tests (`backend/tests/`)
- pytest with parallel execution (`-n auto`)
- Async test support
- Fixtures for database and authentication
- Code coverage tracking
- **Run:** `cd backend && make test`

### Integration Tests (`tests/`)
- Shell scripts using curl
- Test OAuth2 flows
- Test API endpoints
- Test security headers (OWASP compliance)
- Test validation (Pydantic + business logic)
- Test partial success/failure scenarios
- **Run:** `make test`

### Test Coverage
See [tests/README.md](../tests/README.md) for detailed test documentation.

## Key Configuration Files

- **`.env`** - Environment variables (database, keycloak, backend config)
- **`docker compose.yml`** - Container orchestration
- **`backend/pyproject.toml`** - Python dependencies and tool configuration
- **`backend/alembic.ini`** - Database migration configuration
- **`keycloak/clients.yaml`** - Test client definitions (oAuth2)
- **`keycloak/roles.yaml`** - Test role definitions
- **`Makefile`** - Development automation

## Authentication & Authorization

- **Protocol:** OAuth2 Client Credentials flow
- **Identity Provider:** Keycloak
- **Token Type:** JWT Bearer tokens
- **Roles:**
  - `sdep_ca` - Competent Authority access
  - `sdep_str` - STR Platform access
  - `sdep_read` - Read operations
  - `sdep_write` - Write operations
