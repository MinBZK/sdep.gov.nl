<h1>Discussion log</h1>

This page described open and closed discussion items.

- [Open](#open)
- [Closed](#closed)

## Open

For selective additional motivation [*], see the text below the table.

| #               | Topic                                                                          |
| :-------------- | :----------------------------------------------------------------------------- |
| **DIS&nbsp;01** | Batches (with partial failures) or 1-1 tranactions [*]                         |
| **DIS&nbsp;02** | Async request/response model [*]                                               |
| **DIS&nbsp;03** | Extra field `Activity.purposeOfStay` (optional)                                |
| **DIS&nbsp;04** | Change `Temporal.startDatetime, endDatetime` => `Temporal.checkin, checkout`   |
| **DIS&nbsp;05** | CA to filter activities by timestamp (begin/end), e.g. to get a monthly report |
| **DIS&nbsp;06** | Pagination max# records [*]                                                    |
| **DIS&nbsp;07** | Number/country of guests optional                                              |
| **DIS&nbsp;08** | Support for units [*]                                                          |
| **DIS&nbsp;09** | Max #records in POST (throttling) [*]                                          |
| **DIS&nbsp;10** | Unique constraint on area_id + competent_authority_id [*]                      |
| **DIS&nbsp;11** | Unique constraint on activity_id + platform_id [*]                             |

**DIS 01**
- For POST requests, consider to support only one record at a time, or allow batches (as currently supported in prototype)
- When batches, then support partial failures (return succes & failed record)
- When partial failures, then nested transactions are needed
- When nested transactions, then compare single/batch with a performance test

**DIS 02**
- For POST requests, consider an async request/response model
- That is: acknowledge receipt, process the transactions asynchronously
- Consideration: complexity API needs to be extended (push/pull the batch status)
- Consideration: performance gain (test)?
- Consideration: when SDEP is down is not an issue => transaction is rolled back, SDEP is an OLTP-batch system => try again
- **Proposal**: for now, don't do

**DIS 06**
- Keep number of guests and country of guests as optional (in activity)?
- Because these may unavailable in the platform's internal administration
- Consideration: is OK for EU ?

**DIS 08**
- Inside SDEP, or outside SDEP (only in platform administartion, via platformActivityId)

**DIS 09**
- Common approach: max. 1000 ?

**DIS 10**
- Becaue when functionallty supplied by competent authority, duplicates can occur?

**DIS 11**
- Becaue when functionallty supplied by platform, duplicates can occur?

## Closed