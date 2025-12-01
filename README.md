<h1>Welcome to the Single Digital Entry Point (SDEP)</h1>

SDEP Netherlands:

- https://sdep.gov.nl/api/v0/docs

Overview:

- [Quick start](#quick-start)
- [Background](#background)
- [Main functionality](#main-functionality)
- [Documentation](#documentation)


## Quick start

Run locally (fullstack):

- Press Authorize.
- Use client credentials from [client.yaml](./keycloak/client.yaml).

```
make up
```


Test locally (fullstack):
```
make test
```

Run locally (backend only):
```
cd backend
make up
```

Test locally (backend only):
```
cd backend
make test
```

## Background

SDEP is required by EU legislation.

https://eur-lex.europa.eu/eli/reg/2024/1028/oj/eng

## Main functionality

SDEP main functionality is:

- To **ingest regulated areas** from competent authorities (CA)
- To **ingest rental activity data** from short-term rental platforms (STR)
- To **expose rental activity data** to other stakeholders

## Documentation

- [Architecture](./docs/ARCHITECTURE.md)
- [Datamodel](./docs/CLASSES.md)
- [Structure](./docs/CODE.md)
