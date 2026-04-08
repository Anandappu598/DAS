# Unified Add Item Endpoint - Implementation Guide

## Endpoint
**POST** `/api/today-plan/add_item/`

## Purpose
Single unified endpoint that handles **both** catalog items and custom tasks without needing to call different endpoints.

---

## Usage Examples

### 1. Add a Custom Task (from catalog-tasks)
```json
POST /api/today-plan/add_item/

{
  "item_type": "custom",
  "title": "auth",
  "plan_date": "2026-04-08",
  "planned_duration_minutes": 60,
  "quadrant": "Q1",
  "is_unplanned": false,
  "description": "Optional description",
  "user_id": "45"
}
```

**Response (201 Created):**
```json
{
  "message": "Custom item added to today's plan successfully",
  "item_type": "custom",
  "plan": {
    "id": 123,
    "user": 45,
    "custom_title": "auth",
    "custom_description": "Optional description",
    "plan_date": "2026-04-08",
    "quadrant": "Q1",
    "planned_duration_minutes": 60,
    "is_unplanned": false,
    ...
  }
}
```

---

### 2. Add a Catalog Item (from /api/catalog/)
```json
POST /api/today-plan/add_item/

{
  "item_type": "catalog",
  "catalog_id": 5,
  "plan_date": "2026-04-08",
  "quadrant": "Q1",
  "is_unplanned": false,
  "user_id": "45"
}
```

**Response (201 Created):**
```json
{
  "message": "Catalog item added to today's plan successfully",
  "item_type": "catalog",
  "plan": {
    "id": 124,
    "user": 45,
    "catalog_item": 5,
    "plan_date": "2026-04-08",
    "quadrant": "Q1",
    "planned_duration_minutes": 120,
    "is_unplanned": false,
    ...
  }
}
```

---

## Request Parameters

### Common Fields (Both Types)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `item_type` | string | ✅ Yes | Either `"custom"` or `"catalog"` |
| `plan_date` | string | No | Date in format `YYYY-MM-DD`. Defaults to today |
| `quadrant` | string | No | Q1, Q2, Q3, or Q4. Defaults to Q2 |
| `is_unplanned` | boolean | No | Mark as unplanned work. Defaults to false |
| `user_id` | integer | No | For admin/manager to add items for another user |

### Custom Task Only (`item_type: "custom"`)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | string | ✅ Yes | Task title |
| `planned_duration_minutes` | integer | No | Duration in minutes. Defaults to 30 |
| `description` | string | No | Task description |
| `scheduled_start_time` | string | No | Time in HH:MM or HH:MM:SS format |
| `scheduled_end_time` | string | No | Time in HH:MM or HH:MM:SS format |

### Catalog Item Only (`item_type: "catalog"`)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `catalog_id` | integer | ✅ Yes | ID of the catalog item to add |
| `scheduled_start_time` | string | No | Time in HH:MM or HH:MM:SS format |
| `scheduled_end_time` | string | No | Time in HH:MM or HH:MM:SS format |
| `planned_duration_minutes` | integer | No | Duration. Auto-calculated if not provided |

---

## Error Responses

### Invalid item_type
```json
{
  "error": "item_type must be either 'custom' or 'catalog'"
}
(400 Bad Request)
```

### Missing required field for custom task
```json
{
  "error": "title is required for custom tasks"
}
(400 Bad Request)
```

### Missing required field for catalog item
```json
{
  "error": "catalog_id is required for catalog items"
}
(400 Bad Request)
```

### Catalog item not found
```json
{
  "error": "Catalog item not found"
}
(404 Not Found)
```

### No user available
```json
{
  "error": "No user available"
}
(400 Bad Request)
```

---

## Frontend Integration

### From Catalog-Tasks (Project Tasks)
```javascript
// When user drags a task from /api/catalog-tasks/
const task = catalogTaskData;  // { id, title, description, ... }

const payload = {
  item_type: "custom",
  title: task.title,
  plan_date: selectedDate,
  planned_duration_minutes: 60,
  quadrant: selectedQuadrant,
  is_unplanned: false,
  description: task.description
};

fetch('/api/today-plan/add_item/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});
```

### From Catalog
```javascript
// When user drags an item from /api/catalog/
const catalogItem = catalogData;  // { id, name, ... }

const payload = {
  item_type: "catalog",
  catalog_id: catalogItem.id,
  plan_date: selectedDate,
  quadrant: selectedQuadrant,
  is_unplanned: false
};

fetch('/api/today-plan/add_item/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});
```

---

## Backward Compatibility

The old endpoints still exist for backward compatibility:
- `POST /api/today-plan/add_custom/` - Can be deprecated
- `POST /api/today-plan/add_from_catalog/` - Can be deprecated

**Recommendation:** Update frontend to use the unified endpoint, then optionally deprecate the old endpoints in a future release.

---

## Implementation Details

### Logic Flow
1. **Validate item_type** - Must be "custom" or "catalog"
2. **Get/resolve user** - Handle authenticated, anonymous, and admin override cases
3. **Calculate order_index** - For ordering items in today's plan
4. **Branch on item_type:**
   - **Custom**: Extract title, description, duration → create TodayPlan with custom_title/custom_description
   - **Catalog**: Extract catalog_id, fetch Catalog → create TodayPlan with catalog_item relationship
5. **Auto-fill missing times** - If scheduled times not provided, auto-generate based on last item's end time
6. **Return success** - TodayPlan record with full serialized data

### Database Storage
Both types save to the same `TodayPlan` table:
- **Custom tasks**: `custom_title` + `custom_description` populated, `catalog_item` = NULL
- **Catalog items**: `catalog_item` populated, `custom_title` + `custom_description` = NULL

---

## Testing with curl

### Test Custom Task
```bash
curl -X POST http://localhost:8000/api/today-plan/add_item/ \
  -H 'Content-Type: application/json' \
  -d '{
    "item_type": "custom",
    "title": "auth",
    "plan_date": "2026-04-08",
    "planned_duration_minutes": 60,
    "quadrant": "Q1",
    "is_unplanned": false
  }'
```

### Test Catalog Item
```bash
curl -X POST http://localhost:8000/api/today-plan/add_item/ \
  -H 'Content-Type: application/json' \
  -d '{
    "item_type": "catalog",
    "catalog_id": 5,
    "plan_date": "2026-04-08",
    "quadrant": "Q1",
    "is_unplanned": false
  }'
```
