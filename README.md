<h1>Welcome to the Single Digital Entry Point (SDEP)</h1>

SDEP Netherlands:

- https://sdep.gov.nl/api/v0/docs

Overview:

- [Quick start](#quick-start)
- [Background](#background)
- [Main functionality](#main-functionality)
- [Unit tests](#unit-tests)
- [Integration tests](#integration-tests)
- [Design](#design)
- [Discussion](#discussion)

## Quick start

On local workstation (tested on Linux, for Windows consider using WSL).

**Pre-requistes**

- Docker installed
- "jq" and "yq" installed
- "make" installed

**Clone this repo**

To your local workstation.

**Run SDEP fullstack**

Incl. local infra (postgres + keycloak + backend):
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


**Run SDEP backend only**

Excl. local infra:
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

Fullstack, using this [coverage](./tests/README.md):
```
make test
make test-verbose
```

Integration tests are also run against real deployments (TST, ACC, PRE, PRD).

These deployments are out of scope of this project, contact SDEP NLD for more info.

https://sdep.gov.nl/api/v0/docs

## Design

- [Datamodel (internal)](./docs/DATAMODEL.md)
- [Architecture](./docs/ARCHITECTURE.md)
- [Design log](./docs/DESIGN.md)

## Discussion

- [Approach](./docs/APPROACH.md)
- [Limitations](./docs/LIMITATIONS.md)
- [Issues](https://github.com/MinBZK/sdep.gov.nl/issues)
