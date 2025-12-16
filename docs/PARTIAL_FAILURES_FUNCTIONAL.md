# Partial Failures - Functional Overview

## What is Partial Failure Support?

When submitting multiple areas or activities in a single request, the SDEP API processes each item **independently**. Some items may succeed while others fail - this is called **partial success** or **partial failure**.

## Why Partial Failures?

### Problem
Without partial failure support:
```
Submit 100 activities → 1 has an error → ALL 100 rejected
```
Result: 99 valid activities are lost due to 1 error

### Solution
With partial failure support:
```
Submit 100 activities → 1 has an error → 99 saved, 1 rejected
```
Result: Maximum data preserved, clear error reporting for failed items

## How It Works

### Request: Batch Submission
```json
POST /ca/areas
{
  "areas": [
    {
      "competentAuthorityAreaId": "area-001",
      "filename": "area1.zip",
      "filedata": "..."
    },
    {
      "competentAuthorityAreaId": "area-002",
      "filename": "area2.zip",
      "filedata": "..."
    },
    {
      "competentAuthorityAreaId": "INVALID!!!",  // Error: invalid format
      "filename": "area3.zip",
      "filedata": "..."
    }
  ]
}
```

### Response: Partial Success (HTTP 200)
```json
{
  "totalProcessed": 3,
  "succeeded": 2,
  "failed": 1,
  "results": {
    "succeeded": [
      {"index": 0, "message": "Area created successfully"},
      {"index": 1, "message": "Area created successfully"}
    ],
    "failed": [
      {
        "index": 2,
        "errors": [
          {
            "loc": ["areas", 2, "competentAuthorityAreaId"],
            "msg": "Area ID must contain only lowercase alphanumeric characters and dashes",
            "type": "value_error"
          }
        ]
      }
    ]
  }
}
```

**Outcome**:
- ✅ Areas 0 and 1 are saved to database
- ❌ Area 2 failed validation - NOT saved
- HTTP 200 (partial success) with detailed results

## HTTP Status Codes

| Status | Meaning | When Used |
|--------|---------|-----------|
| **201 Created** | Complete success | ALL items succeeded |
| **200 OK** | Partial success | SOME items succeeded, SOME failed |
| **400 Bad Request** | Complete failure | NO items succeeded (all failed validation/business logic) |
| **401 Unauthorized** | Authentication failure | Invalid or missing token |
| **422 Unprocessable Entity** | Request format error | JSON malformed, wrong field types, etc. |

### Decision Tree

```
Submit batch request
  ↓
All items succeed?
  YES → HTTP 201 Created
  NO → Continue
  ↓
Some items succeed?
  YES → HTTP 200 OK (partial success)
  NO → HTTP 400 Bad Request (complete failure)
```

## Response Structure

### Complete Success (HTTP 201)
```json
{
  "totalProcessed": 5,
  "succeeded": 5,
  "failed": 0,
  "results": {
    "succeeded": [
      {"index": 0, "message": "Area created successfully"},
      {"index": 1, "message": "Area created successfully"},
      {"index": 2, "message": "Area created successfully"},
      {"index": 3, "message": "Area created successfully"},
      {"index": 4, "message": "Area created successfully"}
    ],
    "failed": []
  }
}
```

### Partial Success (HTTP 200)
```json
{
  "totalProcessed": 5,
  "succeeded": 3,
  "failed": 2,
  "results": {
    "succeeded": [
      {"index": 0, "message": "Area created successfully"},
      {"index": 2, "message": "Area created successfully"},
      {"index": 4, "message": "Area created successfully"}
    ],
    "failed": [
      {
        "index": 1,
        "errors": [
          {
            "loc": ["areas", 1, "filename"],
            "msg": "filename is required",
            "type": "value_error.missing"
          }
        ]
      },
      {
        "index": 3,
        "errors": [
          {
            "loc": ["areas", 3, "filedata"],
            "msg": "filedata exceeds maximum size of 1MB",
            "type": "value_error"
          }
        ]
      }
    ]
  }
}
```

### Complete Failure (HTTP 400)
```json
{
  "totalProcessed": 3,
  "succeeded": 0,
  "failed": 3,
  "results": {
    "succeeded": [],
    "failed": [
      {
        "index": 0,
        "errors": [{"loc": ["areas", 0, "filename"], "msg": "...", "type": "..."}]
      },
      {
        "index": 1,
        "errors": [{"loc": ["areas", 1, "filename"], "msg": "...", "type": "..."}]
      },
      {
        "index": 2,
        "errors": [{"loc": ["areas", 2, "filedata"], "msg": "...", "type": "..."}]
      }
    ]
  }
}
```

## Error Types

### Validation Errors (Caught Early)
**Where**: Schema validation (Pydantic)
**When**: Before database operations
**Examples**:
- Missing required fields
- Wrong field types (`string` instead of `integer`)
- Invalid formats (email, URL, pattern violations)

```json
{
  "index": 2,
  "errors": [
    {
      "loc": ["activities", 2, "areaId"],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```

### Business Logic Errors (Caught During Processing)
**Where**: Service layer validation
**When**: After schema validation, before database save
**Examples**:
- Referenced entity doesn't exist (e.g., invalid `areaId`)
- Business rule violations

```json
{
  "index": 5,
  "errors": [
    {
      "loc": ["activities", 5, "areaId"],
      "msg": "Area with id 999 not found",
      "type": "business_logic_error"
    }
  ]
}
```

### Database Errors (Caught During Save)
**Where**: CRUD layer
**When**: During database transaction
**Examples**:
- Unique constraint violations
- Foreign key violations (unexpected)
- Check constraint violations

```json
{
  "index": 3,
  "errors": [
    {
      "loc": ["areas", 3],
      "msg": "Database constraint violation: Unique constraint on (competent_authority_id, competent_authority_area_id, created_at)",
      "type": "database_error"
    }
  ]
}
```

## Use Cases

### Use Case 1: Data Migration
**Scenario**: Migrating 1000 historical activities from legacy system

**Approach**:
```bash
# Submit in batches of 100
for batch in batches:
    response = POST /str/activities with 100 activities

    if response.failed > 0:
        log failed items
        retry failed items after fixing errors
```

**Benefit**: Don't lose progress if some items have issues

### Use Case 2: Daily Batch Upload
**Scenario**: Platform submits daily activity report with 500 activities

**Approach**:
```bash
response = POST /str/activities with 500 activities

if response.succeeded == 500:
    # Perfect - all saved
    mark_batch_complete()
elif response.succeeded > 0:
    # Partial - save failed items for review
    save_failed_for_manual_review(response.failed)
    mark_batch_partially_complete()
else:
    # All failed - investigate systemic issue
    alert_administrator()
```

**Benefit**: Automated processing with exception handling

### Use Case 3: Real-time Submission
**Scenario**: Web form submitting single activity

**Approach**:
```javascript
const response = await POST('/str/activities', {
  activities: [singleActivity]
});

if (response.succeeded === 1) {
  showSuccess("Activity submitted!");
} else {
  showErrors(response.results.failed[0].errors);
}
```

**Benefit**: Clear error feedback for user correction

## Best Practices

### 1. Always Check `totalProcessed`, `succeeded`, and `failed`
```python
response = submit_areas(areas)

if response['failed'] > 0:
    # Handle failures
    for failure in response['results']['failed']:
        log_error(failure)
        retry_or_alert(failure)
```

### 2. Use Batch Sizes That Balance Performance and Error Handling
- Too small (1-10): Many requests, slower
- Too large (>1000): Hard to manage failures
- **Recommended**: 50-200 items per batch

### 3. Implement Retry Logic for Failed Items
```python
failed_items = extract_failed_items(response)

for item in failed_items:
    if is_retryable(item):
        retry_with_exponential_backoff(item)
    else:
        alert_for_manual_review(item)
```

### 4. Log All Responses for Audit Trail
```python
log_submission({
    'timestamp': now(),
    'total': response['totalProcessed'],
    'succeeded': response['succeeded'],
    'failed': response['failed'],
    'failed_details': response['results']['failed']
})
```

## FAQ

**Q: If one item fails, does it roll back the others?**
A: No. Each item is processed independently. Successful items are committed even if others fail.

**Q: What if my batch has 100 items and 50 fail?**
A: You'll get HTTP 200 with `succeeded: 50, failed: 50`. The 50 successful items are saved.

**Q: Can I retry just the failed items?**
A: Yes! Extract failed items from the response and resubmit them (after fixing errors).

**Q: What's the maximum batch size?**
A: Check API documentation. Typical limits are 100-1000 items.

**Q: Does the API preserve the order?**
A: The `index` field in responses corresponds to the position in your request array.

## Summary

✅ **Partial failure support maximizes data preservation**
✅ **Clear error reporting per item**
✅ **Suitable for batch processing and real-time submissions**
✅ **Independent transaction per item**
✅ **Enables automated retry workflows**
