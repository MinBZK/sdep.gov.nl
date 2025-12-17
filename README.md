<h1>Welcome to the Single Digital Entry Point (SDEP)</h1>

SDEP Netherlands:

- https://sdep.gov.nl/api/v0/docs

Overview:

- [Quick start (local workstation)](#quick-start-local-workstation)
- [Background](#background)
- [Main functionality](#main-functionality)
- [Unit tests](#unit-tests)
- [Integration tests](#integration-tests)
- [Documentation](#documentation)
- [Discussion and decision log](#discussion-and-decision-log)

## Quick start (local workstation)

**Pre-requistes**

- Docker installed
- "jq" and "yq" installed

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
- Swagger will obtain a JWT bearer token "under the hood" (acting on the `token/` endpoint)
- You are authorized by roles

Explore endpoints in your current role (ca, str).


**Run SDEP backend only** (without local infra)
```
cd backend
make up
```

**Explore all options**
```
make
```

## Background

SDEP is required by EU legislation.

https://eur-lex.europa.eu/eli/reg/2024/1028/oj/eng

## Main functionality

Ingest and expose:

- To **ingest regulated areas** from competent authorities (CA)
- To **expose regulated areas** to short-term rental platforms (STR)
- To **ingest rental activities** from short-term rental platforms
- To **expose rental activities** to competent authorities and other stakeholders

## Unit tests

Backend only:
```
cd backend
make test
make test-verbose
```

## Integration tests

Fullstack, using this [coverage](./test/README.md):
```
make test
make test-verbose
```

Integration tests are also run against real deployments (TST, ACC, PRE, PRD).

These deployments are out of scope of this project, contact SDEP NLD for more info.

https://sdep.gov.nl/api/v0/docs

## Documentation

- [Architecture](./docs/ARCHITECTURE.md)
- [Datamodel](./docs/DATAMODEL.md)
- [ID-management](./docs/ID_DESIGN.md)

## Discussion and decision log

- [Discussion log](./docs/DISCUSSIONS.md)
- [Decision log](./docs/DECISIONS.md)
