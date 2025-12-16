<h1>Discussion log</h1>

This page described open and closed discussion items.

- [Open](#open)
- [Closed](#closed)

## Open

For selective additional motivation, see the text below the table.

| #               | Discussion                         |
| :-------------- | :--------------------------------- |
| **DIS&nbsp;02** | Async request/response model?      |
| **DIS&nbsp;04** | Checkin/checkout?                  |
| **DIS&nbsp;05** | Query filters?                     |
| **DIS&nbsp;06** | Pagination max# records?           |
| **DIS&nbsp;07** | Number/country of guests optional? |
| **DIS&nbsp;08** | Support for units?                 |
| **DIS&nbsp;09** | Max #records in POST (throttling)? |

**DIS 02**
- For POST requests, support an **async request/response model**
- This is: acknowledge receipt, process the transactions asynchronously
- Consideration: API needs to be extended (status back-reporting)
- Consideration: performance test?
- Consideration: when SDEP is down is not an issue => transaction is rolled back, SDEP is an OLTP-batch system => try again
- **Proposal**: for now, don't do

**DIS 03**
- Add `Activity.purposeOfStay` (as optional field)?
- **Discuss**

**DIS 04**
- Change from `Temporal.startDatetime, endDatetime` to `Temporal.checkin, checkout`?
- **Discuss**

**DIS 05**
- CA can filter activities by timestamp (begin/end), e.g. to get a monthly report
- ...
- **Discuss**

**DIS 06**
- Keep number of guests and country of guests as optional (in activity)?
- Because these may unavailable in the platform's internal administration
- Consideration: is OK for EU ?
- **Discuss**

**DIS 08**
- Inside SDEP, or outside SDEP (only in platform administartion, via platformActivityId)
- **Discuss**

**DIS 09**
- Common approach: max. 1000 ?
- **Discuss**

## Closed

| #               | Discussion       | Solution                             |
| :-------------- | :--------------- | :----------------------------------- |
| **DIS&nbsp;01** | Partial failures | See [./DECISIONS.md](./DECISIONS.md) |
