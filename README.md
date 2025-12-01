<h1>Welcome to the Single Digital Entry Point (SDEP)</h1>

SDEP Netherlands:

- https://sdep.gov.nl/api/v0/docs

Overview:

- [Quick start (local workstation)](#quick-start-local-workstation)
- [Background](#background)
- [Main functionality](#main-functionality)
- [Documentation](#documentation)

## Quick start (local workstation)

**Run SDEP fullstack** (incl. local infra)
```
make up
```

Once SDEP is running, explore the Backend API docs in the Swagger UI.

- In the Swagger UI, select Authorize
- Enter client credentials (choose `id`, `secret` from [client.yaml](./keycloak/client.yaml))
- Select Authorize again
- Swagger will obtain a bearer token "under the hood" (by acting on the `token/` endpoint)
- Result: you can start testing the other endpoints

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

## Background

SDEP is required by EU legislation.

https://eur-lex.europa.eu/eli/reg/2024/1028/oj/eng

## Main functionality

- To **ingest regulated areas** from competent authorities (CA)
- To **ingest rental activity data** from short-term rental platforms (STR)
- To **expose rental activity data** to other stakeholders

## Documentation

- [Architecture](./docs/ARCHITECTURE.md)
- [Datamodel](./docs/CLASSES.md)
- [Structure](./docs/CODE.md)
