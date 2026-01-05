<h1>IDs</h1>

SDEP uses:

- On the **“outside”**, only **functional IDs**
- These are logical IDs, business identifiers

SDEP uses:

- On the **“inside”** (under the hood), **technical IDs**
- These are used for referential integrity within the database

Functional IDs:

- May be provided by competent authorities or platforms if desired
- If not, they are generated according to the UID / RFC 9562 standard (except for `platformId` and `competentAuthorityId`, which are supplied by the authorization provider)
- After a POST, the functional IDs are always returned/made visible
- This allows them to be reused in subsequent submissions
- This also enables versioning (in combination with a timstamp)

https://datatracker.ietf.org/doc/rfc9562/
