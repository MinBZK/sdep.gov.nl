<h1>Decision log</h1>

**Keep the API as simple and concise as possible**.

*REST APIs are one of the most common kinds of web interfaces available today. Therefore, it's very important to design REST APIs properly so that we won't run into problems down the road.*

*Otherwise, we create problems for clients that use our APIs, which isn’t pleasant and detracts people from using our API.*

*If we don’t follow commonly accepted conventions, then we confuse the maintainers of the API and the clients that use them since it’s different from what everyone expects.*

https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/


**Table of content**

- [Approach](#approach)
- [API](#api)
- [Security](#security)
- [Discussion list](#discussion-list)

## Approach

- Work technically together with actively participating EU Member States
- Work technically together with actively participating platforms
- Take shared, commonly supported design decisions
- Implement changes quick, to stay agile
- Use GitHub tags for initial versioning
- Use API versioning later (once CAs and platforms are connected)

## API

For additional motivation [*], see the text below the table.

| #               | Decision                                           | Example                                                                                                                |
| :-------------- | :------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------- |
| **API&nbsp;01** | Support OpenAPI 3.1.0 [*]                          |                                                                                                                        |
| **API&nbsp;02** | All endpoints are well-documented                  | See e.g. `/str/activities` endpoint                                                                                    |
| **API&nbsp;03** | Use nouns instead of verbs [*]                     | `/ca/areas`                                                                                                            |
| **API&nbsp;04** | Use plurals for resources                          | `/ca/areas`                                                                                                            |
| **API&nbsp;05** | Consistent datamodel [*]                           | `Activity`, `Area`                                                                                                     |
| **API&nbsp;06** | Consistent endpoints                               | `/ca/areas`, `/ca/activities`, `/str/areas`,`/str/activities`                                                          |
| **API&nbsp;07** | Consistent pagination                              | `offset`, `limit`, all endpoints                                                                                       |
| **API&nbsp;08** | Syntax validation                                  | `postal code`, ...                                                                                                     |
| **API&nbsp;09** | Semantical validation                              | `begin timestamp < end timestamp`                                                                                      |
| **API&nbsp;10** | Integrity validation and the use of ids            |                                                                                                                        |
| **API&nbsp;11** | Transaction size constraints (POST)                | Limit bulk updates to e.g. max 1000 [*]                                                                                |
| **API&nbsp;12** | Logical ordening => readability                    | See e.g. `/str/areas` endpoint                                                                                         |
| **API&nbsp;13** | Essentiality                                       | Only `areaId` in `POST /str/activities`; `competentAuthorityId, competentAuthorityName` are redundant and not required |
| **API&nbsp;14** | Essentiality/security                              | In POST, no need to include the submitter id in the request (competentAuthorityId, platformId)                         |
| **API&nbsp;15** | Consistent HTTP response codes                     | 200, 201, 400, 401, 403, 409, 422                                                                                      |
| **API&nbsp;16** | Submit activities always against current areas [*] |                                                                                                                        |

Motivation:

**API 01**

- Swagger 2.0 is legacy - https://swagger.io/specification/

**API 03**

- Best practice - https://restfulapi.net/resource-naming/, https://logius-standaarden.github.io/API-Design-Rules

**API 05**

- No code duplication** between `ca-area` and `str-area`, if CA requires activity subset, then filter out themselves (activities.activity.areaId)
- Consistent use of Address

**API 11**

- To ensure predictable performance, limit transaction size, and improve reliability and error handling.

**API 16**

- When a platform submits new activities, the platform first has to retrieve the current areas
- Because these may have changed over time
- This way, activities can always be correlated to the areas at that moment in time => point-in-time consistency

## Security

For additional motivation [*], see the text below the table.

| #               | Decision                                                                       | Example |
| :-------------- | :----------------------------------------------------------------------------- | :------ |
| **SEC&nbsp;01** | oAuth2 with JWT [*]                                                            |         |
| **SEC&nbsp;02** | Client credentials grant (client credentials flow) [*]                         |         |
| **SEC&nbsp;03** | Support for delegated API-invocation (smaller platforms via third-parties) [*] |         |

Motivation:

**SEC 01**

- For trusted machine-to-machine (M2M) interaction - https://datatracker.ietf.org/doc/html/rfc6749#section-4.4

**SEC 02**

- Only client credentials grant (client credentials flow)
- Implicit flow (obtain access token directly, without backend secret) is deprecated

**SEC 03**

- Smaller platforms may deliver rental activities to third-parties (by mail, excel, ...)
- API invocation to SDEP is in this case delegated to those third-parties
- Third-party is registered as platform (STR) in SDEP => one STR registration per delegating platform
- Communication between third party and SDEP happens via the regular SDEP API
- STR data remains stored per platform

## Discussion list

Moved to [./DISCUSSIONS.md](./DISCUSSIONS.md).