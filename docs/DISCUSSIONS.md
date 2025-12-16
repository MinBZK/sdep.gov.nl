<h1>Discussion log</h1>

This page described open and closed discussion items.

- [Open](#open)
- [Closed](#closed)

## Open

For additional motivation, see the text below the table.

| #               | Discussion                         | Example |
| :-------------- | :--------------------------------- | :------ |
| **DIS&nbsp;02** | Async request/response model       |         |
| **DIS&nbsp;03** | Purpose of stay                    |         |
| **DIS&nbsp;04** | Checkin/checkout                   |         |
| **DIS&nbsp;05** | Query by timestamp                 |         |
| **DIS&nbsp;06** | Filter by areaId                   |         |
| **DIS&nbsp;07** | Number/country of guests optional? |         |
| **DIS&nbsp;08** | Units                              |         |

**DIS 02**
- For POST requests, support an **async request/response model**
- Is: acknowledge receipt, process the transactions asynchronously
- Consideration: API needs to be extended (status back-reporting)
- Consideration: performance gain?
- Consideration: when SDEP is down is not an issue => transaction is rolled back, SDEP is an OLTP-batch system => try again

**DIS 03**
- Add `Activity.purposeOfStay` (as optional field)?

**DIS 04**
- Change from `Temporal.startDatetime, endDatetime` to `Temporal.checkin, checkout`?

**DIS 05**
- Add query activities by timestamp
- So CA can e.g. get a monthly report

**DIS 06**
- Add filter activities by areaId
- So CA can do selective reporting

**DIS 07**
- Keep number of guests and country of guests as optional (in activity)?
- Because these may unavailable in the platform's internal administration
- Consideration: is OK for EU ?

**DIS 08**
- Discuss

## Closed

| #               | Discussion       | Solution                             |
| :-------------- | :--------------- | :----------------------------------- |
| **DIS&nbsp;01** | Partial failures | See [./DECISIONS.md](./DECISIONS.md) |
