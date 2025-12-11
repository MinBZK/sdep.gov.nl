<h1>Design decisions</h1>

**Keep the API as simple and concise as possible**.

*REST APIs are one of the most common kinds of web interfaces available today. Therefore, it's very important to design REST APIs properly so that we won't run into problems down the road.*

*Otherwise, we create problems for clients that use our APIs, which isn’t pleasant and detracts people from using our API.*

*If we don’t follow commonly accepted conventions, then we confuse the maintainers of the API and the clients that use them since it’s different from what everyone expects.*

https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/


**Table of content**

- [Approach](#approach)
- [API](#api)
- [Security](#security)

## Approach

- Work technically together with actively participating EU Member States
- Work technically together with actively participating platforms
- Take shared, commonly supported design decisions
- Implement changes quick, to stay agile
- Use GitHub tags for initial versioning
- Use API versioning later (once CAs and platforms are connected)

## API

For motivation, see below table.

| #               | Pattern                             | Example                                                                           |
| :-------------- | :---------------------------------- | :-------------------------------------------------------------------------------- |
| **API&nbsp;01** | OpenAPI 3.1.0                       |                                                                                   |
| **API&nbsp;02** | Nouns instead of verbs              | `/ca/areas`                                                                       |
| **API&nbsp;03** | Plurals for resources               | `/ca/areas`                                                                       |
| **API&nbsp;04** | Consistent datamodel                | `Activity`, `Area`                                                                |
| **API&nbsp;05** | Consistent endpoints                | `/ca/areas`, `/ca/activities`, `/str/areas`,`/str/activities`                     |
| **API&nbsp;06** | Consistent pagination               | `offset`, `limit`, all endpoints                                                  |
| **API&nbsp;07** | Syntax validation                   | `postal code`                                                                     |
| **API&nbsp;08** | Semantical validation               | `begin timestamp < end timestamp`                                                 |
| **API&nbsp;09** | Integrity validation                |                                                                                   |
| **API&nbsp;10** | Transaction size constraints (POST) |                                                                                   |
| **API&nbsp;11** | Consistent, functional ids          | `competentAuthorityId`, `platformId`, `areaId`                                    |
| **API&nbsp;12** | Logical ordening => readability     |                                                                                   |
| **API&nbsp;13** | Essentiality                        | `POST /str/activities` => `areaId` and `competentAuthorityId` (unique constraint) |
| **API&nbsp;14** | Consistent HTTP response codes      | 200, 201                                                                          |

Motivation:

**API 01** Swagger 2.0 is legacy - https://swagger.io/specification/

**API 02** Best practice - https://restfulapi.net/resource-naming/, https://logius-standaarden.github.io/API-Design-Rules

**API 04.a** Avoid code duplication (let CA filter out activityId for reporting when needed, as exception to the rule)

**API 04.b** Consistent use of Address (or consistently choose Unit)

**API 09** Duplicate key error, to avoid reporting inconsistencies (add versioning later on?)

**API 12** For POST, only ids, no redundant names

## Security

For motivation, see below table.

| #               | Pattern                  | Example |
| :-------------- | :----------------------- | :------ |
| **SEC&nbsp;01** | oAuth2 with JWT          |         |
| **SEC&nbsp;02** | client credentials grant |         |

Motivation:

**SEC 01** - For trusted machine-to-machine (M2M) interaction - https://datatracker.ietf.org/doc/html/rfc6749#section-4.4

**SEC 02** - Implicit flow (obtain access token directly, without backend secret) is deprecated