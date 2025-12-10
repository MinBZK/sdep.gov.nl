<h1>Welcome to the Single Digital Entry Point (SDEP)</h1>

SDEP Netherlands:

- https://sdep.gov.nl/api/v0/docs

Overview:

- [Quick start (local workstation)](#quick-start-local-workstation)
- [Background](#background)
- [Main functionality](#main-functionality)
- [Design decisions](#design-decisions)
- [Integration test](#integration-test)
- [Documentation](#documentation)

## Quick start (local workstation)

**Pre-requistes**

- Docker installed
- "yq" installed


**Run SDEP fullstack** (incl. local infra)

Start (postgres + keycloak + backend):
```
make up
```

Explore API docs (Swagger UI):

- http://localhost:8000/api/v0/docs

Select client credentials (by roles):

- Choose `id`, `secret` from [clients.yaml](./keycloak/clients.yaml)

Authorize in Swagger UI:

- Select Authorize
- Enter client credentials
- Select Authorize again
- Swagger will obtain a bearer token "under the hood" (acting on the `token/` endpoint)
- You are authorized by roles

Explore endpoints in your current role (ca, str).

**Run SDEP fullstack tests**
```
make test
```

**Run only SDEP backend** (without local infra)
```
cd backend
make up
```

**Run only SDEP backend tests**
```
cd backend
make test
```

**Explore all options**
```
make
```

## Background

SDEP is required by EU legislation.

https://eur-lex.europa.eu/eli/reg/2024/1028/oj/eng

## Main functionality

- To **ingest regulated areas** from competent authorities (CA)
- To **ingest rental activities** from short-term rental platforms (STR)
- To **expose rental activities** to other stakeholders

## Design decisions

- [Design decisions](./docs/DECISIONS.md)

## Integration test

The local integration tests (`make test`) are also run against deployment in Kubernetes (TST, ACC, PRE, PRD)

This deployment is out of the scope of this project.

Inquire SDEP NL for tips how to re-use.

## Documentation

- [Architecture](./docs/ARCHITECTURE.md)
- [Datamodel](./docs/CLASSES.md)
- [Structure](./docs/CODE.md)
