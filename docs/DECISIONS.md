<h1>Design decisions</h1>

*REST APIs are one of the most common kinds of web interfaces available today. Therefore, it's very important to design REST APIs properly so that we won't run into problems down the road.*

*Otherwise, we create problems for clients that use our APIs, which isn’t pleasant and detracts people from using our API.*

*If we don’t follow commonly accepted conventions, then we confuse the maintainers of the API and the clients that use them since it’s different from what everyone expects.*

https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/


**Table of content**

- [API best-practice](#api-best-practice)

## API best-practice

| Pattern                                      | OK in SDEP NL ?         | OK in prototype?           |
| -------------------------------------------- | ----------------------- | -------------------------- |
| Use nouns instead of verbs in endpoint paths | Yes, GET /ca/activities | Yes, GET /ca/activity-data |
| Use of plurals in API endpoint               | Yes, GET /ca/activities | **No, GET /ca/activity-data**  |


https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/

https://restfulapi.net/resource-naming/

https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/
