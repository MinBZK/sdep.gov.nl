<h1>Discussion log</h1>

This page describes discussion items.

When discussed, they will entered as regular issues.

For additional motivation [*], see the text below the table.

| #                   | Topic                                                                           |
| :------------------ | :------------------------------------------------------------------------------ |
| **DIS&nbsp;01** [*] | Async request/response model                                                    |
| **DIS&nbsp;02**     | Extra field `Activity.purposeOfStay` (optional)                                 |
| **DIS&nbsp;03**     | Change `Temporal.startDatetime, endDatetime` into `Temporal.checkin, checkout`? |
| **DIS&nbsp;04**     | CA to filter activities by timestamp (begin/end), e.g. to get a monthly report  |
| **DIS&nbsp;05** [*] | Number/country of guests optional                                               |
| **DIS&nbsp;06** [*] | Support for units [*]                                                           |


**DIS 01**
- For POST requests, consider an async request/response model
- That is: acknowledge receipt, process the transactions asynchronously
- Complexity: API needs to be extended for reporting back the status of each record
- For example: what happens when a validation error occurs on storing the submitted data
- Consideration: performance gain (test)?
- Consideration: when SDEP is down, this is not an issue => the entire transaction is rolled back => try again later

**DIS 05**
- Keep number of guests and country of guests as optional (in activity)?
- Because these may unavailable in the platform's internal administration
- Consideration: is OK for EU ?

**DIS 08**
- As concept inside SDEP, or implicitly handled by platforms outside SDEP (and submitted via activityId)
