# Activity Log Completion API Update

## Overview
The Activity Log completion endpoint has been enhanced to allow users to specify custom start/end times and record extra hours worked when completing a task.

## New Fields Added to ActivityLog Model

1. **user_start_time** (DateTimeField, optional)
   - User-specified start time when completing the task
   - If not provided, uses the automatically recorded `actual_start_time`

2. **user_end_time** (DateTimeField, optional)
   - User-specified end time when completing the task  
   - If not provided, uses the automatically recorded `actual_end_time`

3. **extra_hours** (DecimalField, default=0)
   - Additional hours worked beyond the calculated time
   - Useful when user worked extra hours that weren't tracked

## API Endpoint

### Complete an Activity Log
**Endpoint:** `POST /api/activity-logs/{id}/stop/`

**Request Body:**
```json
{
  "is_completed": true,
  "work_notes": "Task completed successfully",
  "user_start_time": "2026-02-14T09:00:00Z",  // Optional: ISO 8601 format
  "user_end_time": "2026-02-14T15:30:00Z",    // Optional: ISO 8601 format
  "extra_hours": 2.5,                          // Optional: decimal hours (e.g., 2.5 = 2 hours 30 minutes)
  "minutes_left": 0
}
```

**For Stopped (Not Completed):**
```json
{
  "is_completed": false,
  "work_notes": "Need more time",
  "reason": "Unexpected complexity",
  "minutes_left": 120
}
```

## Time Calculation Logic

The system calculates total hours worked as follows:

1. **Base Time Calculation:**
   - If `user_start_time` and `user_end_time` are provided: uses those
   - Otherwise: uses `actual_start_time` and `actual_end_time`

2. **Extra Hours:**
   - Adds `extra_hours` to the base calculated time
   - Formula: `total_hours = (end_time - start_time) + extra_hours`

3. **Example:**
   - User started at 9:00 AM, ended at 5:00 PM = 8 hours
   - User adds 2 extra hours = Total 10 hours recorded

## Response

```json
{
  "message": "Task completed successfully!",
  "activity_log": {
    "id": 123,
    "user": 1,
    "today_plan": 456,
    "actual_start_time": "2026-02-14T08:45:00Z",
    "actual_end_time": "2026-02-14T15:00:00Z",
    "user_start_time": "2026-02-14T09:00:00Z",
    "user_end_time": "2026-02-14T15:30:00Z",
    "extra_hours": 2.5,
    "hours_worked": 9.0,
    "minutes_worked": 540,
    "status": "COMPLETED",
    "is_task_completed": true,
    "work_notes": "Task completed successfully"
  }
}
```

## Frontend Integration

When showing the completion dialog:

1. **Ask for Start Time:** Display datetime picker for when they actually started
2. **Ask for End Time:** Display datetime picker for when they actually ended  
3. **Ask for Extra Hours:** Input field for any additional hours worked
4. **Optional:** Pre-populate with actual recorded times, allow user to adjust

## Use Cases

### Use Case 1: User works exact tracked time
```json
{
  "is_completed": true
  // No custom times needed - uses auto-tracked times
}
```

### Use Case 2: User forgot to start timer on time
```json
{
  "is_completed": true,
  "user_start_time": "2026-02-14T08:00:00Z",  // They actually started at 8 AM
  "user_end_time": "2026-02-14T17:00:00Z"     // but clicked start at 9 AM
}
```

### Use Case 3: User worked extra hours after hours
```json
{
  "is_completed": true,
  "extra_hours": 3.0  // Worked 3 extra hours from home in the evening
}
```

### Use Case 4: Combination
```json
{
  "is_completed": true,
  "user_start_time": "2026-02-14T08:30:00Z",
  "user_end_time": "2026-02-14T16:00:00Z",
  "extra_hours": 1.5  // Plus 1.5 hours later
}
```

## Migration

The migration `0021_activitylog_extra_hours_and_times.py` has been created and applied.

Run if needed:
```bash
python manage.py migrate
```

## Notes

- All time fields accept ISO 8601 format datetime strings
- `extra_hours` accepts decimal values (e.g., 1.5 = 1 hour 30 minutes)
- The system automatically calculates `hours_worked` and `minutes_worked`
- Previous behavior is maintained if no custom times are provided
