<h1>Discussion log</h1>

This page described open and closed discussion items.

- [Open](#open)
- [Closed](#closed)

## Open

For additional motivation [*], see the text below the table.

| #               | Topic                                                                          |
| :-------------- | :----------------------------------------------------------------------------- |
| **DIS&nbsp;01** | Bulk updates or 1-1 tranactions [*]                                            |
| **DIS&nbsp;02** | Async request/response model [*]                                               |
| **DIS&nbsp;03** | Extra field `Activity.purposeOfStay` (optional)                                |
| **DIS&nbsp;04** | Change `Temporal.startDatetime, endDatetime` => `Temporal.checkin, checkout`   |
| **DIS&nbsp;05** | CA to filter activities by timestamp (begin/end), e.g. to get a monthly report |
| **DIS&nbsp;06** | Pagination max# records [*]                                                    |
| **DIS&nbsp;07** | Number/country of guests optional                                              |
| **DIS&nbsp;08** | Support for units [*]                                                          |
| **DIS&nbsp;09** | Max #records in POST (throttling) [*]                                          |
| **DIS&nbsp;10** | When adding new version => invalidate the previous?                            |

**DIS 01**
- For POST requests, consider to support only one record at a time, or allow bulk updates (as currently supported in prototype)
- When bulk updates, then partial failures are required (return succes records or failed records) => this is currently implemented
- For partial failures, nested transactions are needed
- For nested transactions, performance need to be checked

**DIS 02**
- For POST requests, consider an async request/response model
- That is: acknowledge receipt, process the transactions asynchronously
- Complexity: API needs to be extended for reporting back the status of each record
- For example: what happens when a validation error occurs on storing the submitted data
- Consideration: performance gain (test)?
- Consideration: when SDEP is down, this is not an issue => the entire transaction is rolled back => try again later

**DIS 06**
- Keep number of guests and country of guests as optional (in activity)?
- Because these may unavailable in the platform's internal administration
- Consideration: is OK for EU ?

**DIS 08**
- Inside SDEP, or outside SDEP (only in platform administartion, via platformActivityId)

**DIS 09**
- Common approach: max. 1000 ?

## Closed