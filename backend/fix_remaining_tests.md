# Remaining Test Fixes

## Summary of Required Changes

### 1. Activity CRUD Tests (test/crud/test_activity.py)

**Remove these test functions** (lines 195-274, 374-431):
- `test_update_activity`
- `test_update_activity_address_fields`
- `test_update_activity_temporal_fields`
- `test_update_activity_not_found`
- `test_get_by_platform_activity_id`
- `test_get_by_platform_activity_id_not_found`
- `test_get_by_platform_activity_id_and_platform_id`
- `test_get_by_platform_activity_id_and_platform_id_not_found`

**Update these tests** (lines 492-533):
```python
async def test_get_by_unique_constraint(self, async_session: AsyncSession):
    """Test getting activity by unique constraint (platform_id, platform_activity_id, created_at)."""
    # Arrange
    test_platform_activity_id = "test-activity-unique-001"
    act = await ActivityFactory.create_async(
        async_session,
        platform_activity_id=test_platform_activity_id,
    )
    await async_session.flush()
    await async_session.refresh(act)

    # Act
    result = await activity.get_by_unique_constraint(
        async_session,
        act.platform_id,
        test_platform_activity_id,
        act.created_at
    )

    # Assert
    assert result is not None
    assert result.id == act.id

async def test_get_by_unique_constraint_not_found(self, async_session: AsyncSession):
    """Test getting activity by non-existent unique constraint."""
    # Arrange
    platform = await PlatformFactory.create_async(async_session)
    from datetime import datetime, timezone

    # Act
    result = await activity.get_by_unique_constraint(
        async_session,
        platform.id,
        "nonexistent-activity-id",
        datetime.now(timezone.utc)
    )

    # Assert
    assert result is None
```

### 2. CompetentAuthority CRUD Tests (test/crud/test_competent_authority.py)

**Remove these test functions**:
- `test_update_competent_authority`
- `test_update_competent_authority_not_found`

### 3. Area CRUD Tests (test/crud/test_area.py)

**Fix test_unique_constraint_with_different_timestamps** (add more delay):
```python
# Small delay to ensure different timestamp
import time
time.sleep(0.01)  # Increase from 0.001 to 0.01 seconds
```

### 4. Area Service Tests (test/services/test_area.py)

**Remove these test functions**:
- `test_get_area_by_competent_authority_area_id_not_found`
- `test_get_area_by_competent_authority_area_id_with_data`
- `test_get_area_by_competent_authority_area_id_response_structure`
- `test_get_area_by_competent_authority_area_id_with_large_binary_data`
- `test_get_area_by_competent_authority_area_id_multiple_areas_different_data`

### 5. Activity Service Tests (test/services/test_activity.py)

**Key Issue**: Tests are using old pattern with functional area_id strings. Need to:
1. Create areas and get their technical IDs
2. Use technical IDs in activity payloads

**Example fix pattern**:
```python
# OLD (functional ID):
activity_data = {
    "area_id": "area-functional-id",
    "competent_authority_id": "ca-id",
    ...
}

# NEW (technical ID):
# First create area
area = await AreaFactory.create_async(async_session, ...)
# Then use technical ID
activity_data = {
    "area_id": area.id,  # Integer technical ID
    # No competent_authority_id
    ...
}
```

### 6. STR Areas API Tests (test/api/test_str_areas.py)

**Issue**: Tests using functional ID in GET /str/areas/{areaId}

**Fix**: Use technical ID (integer) instead:
```python
# OLD:
response = await client.get(f"/api/v0/str/areas/amsterdam-area-0363")

# NEW:
area = await AreaFactory.create_async(...)
response = await client.get(f"/api/v0/str/areas/{area.id}")
```

## Quick Fix Commands

Run these to remove obsolete test functions:

```bash
cd backend

# Backup first
cp test/crud/test_activity.py test/crud/test_activity.py.bak
cp test/crud/test_competent_authority.py test/crud/test_competent_authority.py.bak
cp test/services/test_area.py test/services/test_area.py.bak
```

Then manually edit or use sed to remove the specified test functions.
