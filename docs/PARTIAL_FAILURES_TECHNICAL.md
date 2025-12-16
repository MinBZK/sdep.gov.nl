# Partial Failures - Technical Implementation

## Architecture Overview

The partial failure mechanism uses **nested transactions** (savepoints) to ensure each item in a batch is processed independently while maintaining ACID properties.

```
API Request (batch of N items)
  ↓
Transaction Begins
  ↓
For each item in batch:
  ├─ Savepoint Created       (nested transaction)
  ├─ Validation Phase        (schema + business logic)
  ├─ Processing Phase        (CRUD operations)
  ├─ Database Save           (flush within savepoint)
  ├─ Success?
  │   ├─ YES → Release Savepoint (commit nested transaction)
  │   └─ NO  → Rollback to Savepoint (undo nested transaction)
  ↓
Transaction Commits (all successful items committed)
Response Sent (summary + details)
```

## Implementation Layers

### Layer 1: API Endpoint
**File**: `backend/app/api/common/routers/ca_areas.py`, `str_activities.py`

**Responsibilities**:
- Parse and validate request JSON (Pydantic schema)
- Authenticate user (JWT token)
- Delegate to service layer
- Determine HTTP status code based on results
- Format response

**Code Pattern**:
```python
@router.post("/ca/areas")
async def post_areas(
    request: AreaListRequest,
    session: AsyncSession = Depends(get_async_db),
    token_payload: dict = Depends(verify_bearer_token)
):
    # Extract authenticated user info
    client_id = token_payload.get("client_id")
    client_name = token_payload.get("client_name")

    # Convert to service layer format
    areas_service_format = [
        area.to_service_dict(client_id, client_name)
        for area in request.areas
    ]

    # Call service layer (handles partial failures)
    results = await area_service.process_areas(session, areas_service_format)

    # Determine HTTP status
    if results["failed"] == 0:
        status_code = status.HTTP_201_CREATED  # All succeeded
    elif results["succeeded"] > 0:
        status_code = status.HTTP_200_OK  # Partial success
    else:
        status_code = status.HTTP_400_BAD_REQUEST  # All failed

    return JSONResponse(status_code=status_code, content=results)
```

### Layer 2: Service Layer
**File**: `backend/app/services/area.py`, `activity.py`

**Responsibilities**:
- Orchestrate batch processing
- Create savepoints for each item
- Coordinate validation and CRUD operations
- Collect results (successes + failures)
- Return structured response

**Code Pattern**:
```python
async def process_areas(session: AsyncSession, areas: list[dict]) -> dict:
    """
    Process multiple areas with partial failure support.
    Each area is processed in its own savepoint.
    """
    results = {
        "totalProcessed": len(areas),
        "succeeded": 0,
        "failed": 0,
        "results": {
            "succeeded": [],
            "failed": []
        }
    }

    for index, area in enumerate(areas):
        try:
            # Phase 1: Validation (before savepoint)
            errors = await validate_area(session, area, index)
            if errors:
                results["failed"] += 1
                results["results"]["failed"].append({
                    "index": index,
                    "errors": errors
                })
                continue

            # Phase 2: Processing within savepoint
            async with session.begin_nested():  # Start savepoint
                await process_single_area(session, area)
                # If no exception → savepoint commits

            # Success
            results["succeeded"] += 1
            results["results"]["succeeded"].append({
                "index": index,
                "message": "Area created successfully"
            })

        except IntegrityError as e:
            # Database constraint violation
            await session.rollback()  # Rollback savepoint
            results["failed"] += 1
            results["results"]["failed"].append({
                "index": index,
                "errors": [{
                    "loc": ["areas", index],
                    "msg": f"Database constraint violation: {str(e)}",
                    "type": "database_error"
                }]
            })

        except Exception as e:
            # Unexpected error
            await session.rollback()  # Rollback savepoint
            results["failed"] += 1
            results["results"]["failed"].append({
                "index": index,
                "errors": [{
                    "loc": ["areas", index],
                    "msg": f"Unexpected error: {str(e)}",
                    "type": "server_error"
                }]
            })

    return results
```

**Key Design Decisions**:
1. **Validation before savepoint**: Avoid transaction overhead for invalid data
2. **Savepoint per item**: Isolate database operations
3. **Exception handling**: Catch and convert to structured errors

### Layer 3: CRUD Layer
**File**: `backend/app/crud/area.py`, `activity.py`

**Responsibilities**:
- Data access operations
- Use `session.flush()` instead of `session.commit()`
- Let service layer manage transactions

**Code Pattern**:
```python
async def create(
    session: AsyncSession,
    competent_authority_area_id: str | None,
    competent_authority_id: int,
    filename: str,
    filedata: bytes,
) -> Area:
    """Create area. Only flushes - transaction managed by service layer."""
    area = Area(
        competent_authority_area_id=competent_authority_area_id,
        competent_authority_id=competent_authority_id,
        filename=filename,
        filedata=filedata,
    )
    session.add(area)
    await session.flush()  # NOT commit - let service layer manage
    await session.refresh(area)
    return area
```

**Critical**: CRUD functions use `flush()` not `commit()`:
- `flush()`: Writes to database within transaction
- `commit()`: Ends transaction (managed by API dependency)

## Transaction Management

### Database Session Lifecycle

```
HTTP Request Arrives
  ↓
get_async_db dependency creates session
  ↓
Session transaction begins (auto)
  ↓
API endpoint receives session
  ↓
Service layer uses session with savepoints
  │
  ├─ Item 1: savepoint → flush → release
  ├─ Item 2: savepoint → flush → rollback (error)
  ├─ Item 3: savepoint → flush → release
  ...
  ↓
API endpoint returns response
  ↓
Session transaction commits (auto in dependency)
  ↓
Session closed
```

### Savepoint Behavior

**Successful Item**:
```python
async with session.begin_nested():  # Create savepoint SP1
    await area_crud.create(session, ...)  # flush() writes to SP1
    # No exception → SP1 released (changes kept)
# Changes are in parent transaction
```

**Failed Item**:
```python
async with session.begin_nested():  # Create savepoint SP2
    await area_crud.create(session, ...)  # flush() writes to SP2
    # Exception raised
except Exception:
    # SP2 automatically rolled back
# Parent transaction unchanged
```

### PostgreSQL Commands

```sql
-- Start main transaction
BEGIN;

-- Item 1 processing
SAVEPOINT sp_item_0;
INSERT INTO area (...) VALUES (...);
RELEASE SAVEPOINT sp_item_0;  -- Success

-- Item 2 processing
SAVEPOINT sp_item_1;
INSERT INTO area (...) VALUES (...);  -- Violates constraint
ROLLBACK TO SAVEPOINT sp_item_1;  -- Undo item 2 only

-- Item 3 processing
SAVEPOINT sp_item_2;
INSERT INTO area (...) VALUES (...);
RELEASE SAVEPOINT sp_item_2;  -- Success

-- Commit main transaction (Items 1 and 3 saved, Item 2 not saved)
COMMIT;
```

## Validation Phases

### Phase 1: Schema Validation (Pydantic)
**When**: Before service layer processing
**Catches**:
- Missing required fields
- Wrong types
- Format violations (regex, length, etc.)

**Example**:
```python
class AreaRequest(BaseModel):
    competent_authority_area_id: str | None = Field(
        None,
        pattern=r"^[a-z0-9-]+$",  # Validates format
        max_length=64
    )
    filename: str = Field(..., min_length=1)  # Required, non-empty
    filedata: bytes = Field(...)  # Required
```

**Result**: Pydantic raises `ValidationError` → API returns HTTP 422

### Phase 2: Business Logic Validation (Service Layer)
**When**: Before database operations
**Catches**:
- Referenced entities don't exist
- Business rules violated

**Example**:
```python
async def validate_activity(session, activity, index):
    errors = []

    # Validate Area exists
    area_id = activity["area_id"]
    area = await area_crud.get_by_id(session, area_id)
    if area is None:
        errors.append({
            "loc": ["activities", index, "areaId"],
            "msg": f"Area with id {area_id} not found",
            "type": "business_logic_error"
        })

    return errors
```

**Result**: Item skipped (not processed), added to `failed` list

### Phase 3: Database Constraints (CRUD Layer)
**When**: During `flush()` within savepoint
**Catches**:
- Unique constraint violations
- Foreign key violations
- Check constraint violations

**Example**:
```python
try:
    async with session.begin_nested():
        await area_crud.create(session, ...)
except IntegrityError as e:
    # Savepoint rolled back
    # Add to failed results
```

**Result**: Savepoint rolled back, item added to `failed` list

## Error Handling Strategy

### Error Collection Pattern

```python
# Collect errors without stopping processing
for index, item in enumerate(items):
    try:
        # Validation phase
        validation_errors = await validate_item(session, item, index)
        if validation_errors:
            results["failed"].append({
                "index": index,
                "errors": validation_errors
            })
            continue  # Skip to next item

        # Processing phase
        async with session.begin_nested():
            await process_single_item(session, item)

        results["succeeded"].append({"index": index, ...})

    except IntegrityError as e:
        # Database error - savepoint already rolled back
        results["failed"].append({
            "index": index,
            "errors": [format_database_error(e, index)]
        })

    except Exception as e:
        # Unexpected error - rollback and log
        await session.rollback()
        logger.error(f"Unexpected error processing item {index}: {e}")
        results["failed"].append({
            "index": index,
            "errors": [format_server_error(e, index)]
        })

# Continue processing remaining items
```

**Key Points**:
- Use `continue` to skip failed items
- Always collect errors (don't raise exceptions)
- Process all items regardless of individual failures

## Performance Considerations

### Savepoint Overhead
Each savepoint has minimal overhead:
- **PostgreSQL**: ~0.1ms per savepoint
- **Batch of 100**: ~10ms total savepoint overhead

**Optimization**: Pre-validate before savepoint to avoid unnecessary transactions

### Flush vs. Commit
- `flush()`: Writes to database, stays in transaction (~1ms)
- `commit()`: Ends transaction, releases locks (~5ms)

**Pattern**: Use one `commit()` at the end (via dependency), many `flush()` calls within

### Concurrent Requests
Multiple requests can process batches concurrently:
- Each request has its own session/transaction
- Row-level locking prevents conflicts
- Savepoints enable independent item processing within batch

## Testing Strategy

### Unit Tests (Backend Tests)
Test CRUD functions in isolation:
```python
async def test_create_multiple_areas(async_session):
    """Test creating multiple areas with same functional ID (versioning)."""
    ca = await CompetentAuthorityFactory.create_async(async_session)

    # Create first area
    area1 = await area_crud.create(
        async_session,
        competent_authority_area_id="test-area",
        competent_authority_id=ca.id,
        filename="area1.zip",
        filedata=b"data1"
    )
    await async_session.flush()

    # Create second area with same functional ID (versioning)
    area2 = await area_crud.create(
        async_session,
        competent_authority_area_id="test-area",  # Same functional ID
        competent_authority_id=ca.id,
        filename="area2.zip",
        filedata=b"data2"
    )
    await async_session.flush()

    # Both should succeed (no unique constraint)
    assert area1.id != area2.id  # Different technical UUIDs
    assert area1.created_at != area2.created_at  # Different timestamps
    assert area1.competent_authority_area_id == area2.competent_authority_area_id  # Same functional ID
```

### Integration Tests (Shell Scripts)
Test API endpoints with partial failures:
```bash
# Test partial success
PAYLOAD=$(cat <<EOF
{
  "areas": [
    {"competentAuthorityAreaId": "valid-area-1", ...},
    {"competentAuthorityAreaId": "INVALID!!!", ...},  # Will fail
    {"competentAuthorityAreaId": "valid-area-2", ...}
  ]
}
EOF
)

response=$(curl -X POST /ca/areas -d "$PAYLOAD")
succeeded=$(echo "$response" | jq '.succeeded')
failed=$(echo "$response" | jq '.failed')

assert_equals "$succeeded" "2"
assert_equals "$failed" "1"
```

## Debugging

### Enable SQL Logging
```python
# In database config
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Log all SQL statements
)
```

**Output**:
```sql
BEGIN;
SAVEPOINT sp_item_0;
INSERT INTO area (...) VALUES (...);
RELEASE SAVEPOINT sp_item_0;
SAVEPOINT sp_item_1;
INSERT INTO area (...) VALUES (...);
-- ERROR: duplicate key violates unique constraint
ROLLBACK TO SAVEPOINT sp_item_1;
COMMIT;
```

### Log Service Layer Results
```python
logger.info(f"Processed {totalProcessed} items: "
            f"{succeeded} succeeded, {failed} failed")
for failure in results["results"]["failed"]:
    logger.warning(f"Item {failure['index']} failed: {failure['errors']}")
```

## Common Pitfalls

### ❌ Using `commit()` in CRUD Layer
```python
# WRONG
async def create(session, ...):
    session.add(entity)
    await session.commit()  # Don't do this!
```

**Problem**: Commits entire transaction, breaking partial failure isolation

**Solution**: Use `flush()` instead

### ❌ Not Handling Savepoint Exceptions
```python
# WRONG
async with session.begin_nested():
    await process_item(session, item)
# Exception propagates, stops batch processing
```

**Problem**: One failure stops all remaining items

**Solution**: Wrap in try/except

### ❌ Validating After Savepoint
```python
# WRONG
async with session.begin_nested():
    await process_item(session, item)
    if not is_valid(item):  # Validation too late
        raise ValueError()
```

**Problem**: Unnecessary transaction overhead

**Solution**: Validate before savepoint

## Summary

**Architecture**:
- API Layer → Service Layer → CRUD Layer
- Nested transactions (savepoints) for isolation
- `flush()` in CRUD, `commit()` in dependency

**Error Handling**:
- 3 validation phases (schema, business logic, database)
- Collect errors without stopping processing
- Structured error responses

**Performance**:
- Minimal savepoint overhead
- Pre-validation optimization
- Concurrent batch processing supported

**Testing**:
- Unit tests for constraints
- Integration tests for partial failures
- SQL logging for debugging
