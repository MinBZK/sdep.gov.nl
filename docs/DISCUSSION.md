<h1>Discussion</h1>

This page described open and closed discussion items.

- [Open](#open)
- [Closed](#closed)

## Open

For additional motivation, see the text below the table.

| #             | Discussion                         | Example |
| :------------ | :--------------------------------- | :------ |
| **D&nbsp;01** | Partial failures                   |         |
| **D&nbsp;02** | Async request/response model       |         |
| **D&nbsp;03** | Purpose of stay                    |         |
| **D&nbsp;04** | Checkin/checkout                   |         |
| **D&nbsp;05** | Query by timestamp                 |         |
| **D&nbsp;06** | Filter by areaId                   |         |
| **D&nbsp;07** | Number/country of guests optional? |         |

**D 01**
- For POST requests, instead of "all are processed atomically (all succeed or all fail)", **allow partial failures**
- E.g. return OK (HTTP 200) with the original list, extended with a status ID (OK/NOK)
- Consideration: this is implemented in the prototype API
- Consideration: performance (1-1 transactions)

**D 02**
- For POST requests, support an **async request/response model**
- I.e. acknowledge receipt, process the transactions asynchrously
- Consideration: API needs to be extended (status back-reporting)
- Consideration: performance gain for initial POST (when partial
- Consideration: expect performance gain in case of 1-1 transactions
- Consideration: when SDEP is down => is this an issue, because SDEP is an OLTP-batches system => try again
- Consideration: do onyl when needed (functional/technical)

**D 03**
- Addd `Activity.purposeOfStay` (as optional field)

**D 04**
- Change from `Temporal.startDatetime, endDatetime` to `Temporal.checkin, checkout`

**D 05**
- Add query activities by timestamp
- So CA can e.g. get a monthly report

**D 06**
- Add filter activities by areaId
- So CA can do selective reporting

**D 07**
- Keep number of guests and country of guests as optional (in activity)
- Because these may unavailable in the platform's internal administration
- Consideration: is OK for EU ?

## Closed

| #             | Discussion | Example |
| :------------ | :--------- | :------ |
| **D&nbsp;xx** |            |         |
