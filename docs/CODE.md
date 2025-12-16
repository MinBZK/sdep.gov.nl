# Project structure

This document explains the directory structure and organization of the SDEP project.

For architectural concepts, layers, and data flows, see [ARCHITECTURE.md](./ARCHITECTURE.md).

## Root structure
```
.
├── backend/              # Python backend application
├── docs/                 # Documentation
│   ├── ARCHITECTURE.md   # Architecture documentation
│   ├── Datamodel.drawio    # UML class diagram (source)
│   ├── Datamodel.svg       # UML class diagram (rendered)
│   └── CODE.md           # This file
├── keycloak/             # Keycloak IAM configuration
├── docker-compose.yml    # Local development environment
├── Makefile              # Project automation
└── README.md             # Project overview
```

## Root details

- [`backend/`](../backend/) - Python backend application (see Backend structure above)
- [`docs/`](../docs/) - Project documentation
  - [`Architecture.excalidraw`](./Architecture.excalidraw) - Architecture diagram source
  - [`Architecture.png`](./Architecture.png) - Architecture diagram rendered
  - [`ARCHITECTURE.md`](./ARCHITECTURE.md) - Architecture documentation
  - [`Datamodel.drawio`](./Datamodel.drawio) - UML class diagram source
  - [`Datamodel.svg`](./Datamodel.svg) - UML class diagram rendered
  - `CODE.md` - This file
- [`keycloak/`](../keycloak/) - Keycloak IAM server configuration
- [`AGENTS.md`](../AGENTS.md) - Development rules and AI agent instructions
- [`CLAUDE.md`](../CLAUDE.md) - Claude-specific configuration
- [`docker-compose.yml`](../docker-compose.yml) - Local development environment setup
- [`Makefile`](../Makefile) - Project automation commands
- [`README.md`](../README.md) - Project overview and quick start

## Backend structure
```
backend/
├── alembic/              # Database migrations
│   └── versions/         # Migration scripts
├── app/
│   ├── api/              # FastAPI endpoints
│   ├── crud/             # Data access layer
│   ├── db/               # Database configuration
│   ├── exceptions/       # Custom exceptions
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic validation schemas
│   ├── security/         # Authentication & authorization
│   └── services/         # Business logic layer
├── test/
│   ├── api/              # API tests
│   ├── crud/             # CRUD tests
│   ├── fixtures/         # Test fixtures
│   ├── security/         # Security tests
│   └── services/         # Service tests
├── pyproject.toml        # Python dependencies & configuration
└── Makefile              # Build & test automation
```

### Backend details

- [`backend/alembic/`](../backend/alembic/) - Database migrations using Alembic
  - [`versions/`](../backend/alembic/versions/) - Sequential migration scripts
- [`backend/app/api/`](../backend/app/api/) - FastAPI endpoints (transaction demarcation)
- [`backend/app/crud/`](../backend/app/crud/) - CRUD operations (data access with flush)
- [`backend/app/db/`](../backend/app/db/) - Database connection and session management
- [`backend/app/exceptions/`](../backend/app/exceptions/) - Custom exception definitions
- [`backend/app/models/`](../backend/app/models/) - SQLAlchemy ORM models (generated from UML)
- [`backend/app/schemas/`](../backend/app/schemas/) - Pydantic validation schemas
- [`backend/app/security/`](../backend/app/security/) - OAuth2/JWT authentication
- [`backend/app/services/`](../backend/app/services/) - Business logic implementation
- [`backend/test/api/`](../backend/test/api/) - API endpoint tests
- [`backend/test/crud/`](../backend/test/crud/) - CRUD layer tests
- [`backend/test/fixtures/`](../backend/test/fixtures/) - Test fixtures (factory_boy)
- [`backend/test/security/`](../backend/test/security/) - Security tests
- [`backend/test/services/`](../backend/test/services/) - Service layer tests
