# Daily Activity System (DAS) - Workflow Guide

## 🎯 Overview
The DAS project now implements a complete drag-and-drop daily activity management system that allows users to plan, track, and manage their work activities efficiently.

---

## 📋 Core Workflow

### 1. **Catalog Management**
The catalog is your master list of all work items that can be planned for the day.

**Catalog Types:**
- `PROJECT` - Work projects
- `TASK` - Individual tasks
- `COURSE` - Classes or courses
- `ROUTINE` - Regular routines
- `CUSTOM` - Custom work items

**API Endpoints:**
- `GET /api/catalog/` - List all catalog items
- `POST /api/catalog/` - Create new catalog item
- `GET /api/catalog/my_catalog/` - Get your catalog items
- `GET /api/catalog/by_type/?type=PROJECT` - Filter by type

**Example Create Catalog Item:**
```json
POST /api/catalog/
{
  "name": "Backend API Development",
  "description": "Work on user authentication APIs",
  "catalog_type": "PROJECT",
  "project": 1,
  "estimated_hours": 4.5
}
```

---

### 2. **Today's Plan (Drag & Drop)**
Drag items from your catalog to today's plan and set scheduled times.

**API Endpoints:**
- `GET /api/today-plan/today/` - Get today's plan
- `POST /api/today-plan/add_from_catalog/` - Add item from catalog to today's plan
- `POST /api/today-plan/{id}/move_to_activity_log/` - Start working (click arrow)
- `POST /api/today-plan/reorder/` - Reorder plan items

**Example Add to Today's Plan:**
```json
POST /api/today-plan/add_from_catalog/
{
  "catalog_id": 5,
  "plan_date": "2026-02-07",
  "scheduled_start_time": "09:00:00",
  "scheduled_end_time": "13:00:00",
  "planned_duration_minutes": 240,
  "notes": "Focus on authentication and authorization"
}
```

**Status Flow:**
```
PLANNED → STARTED → IN_ACTIVITY → COMPLETED/MOVED_TO_PENDING
```

---

### 3. **Start Your Day**
Before you can start working, you need to start your day session.

**API Endpoints:**
- `POST /api/day-session/start_day/` - Start your work day
- `POST /api/day-session/end_day/` - End your work day
- `GET /api/day-session/current_session/` - Get current session

**Example Start Day:**
```json
POST /api/day-session/start_day/
Response:
{
  "message": "Day started successfully! Let's make it productive!",
  "session": {
    "id": 1,
    "user": 1,
    "session_date": "2026-02-07",
    "started_at": "2026-02-07T08:30:00Z",
    "is_active": true
  },
  "plans_count": 5
}
```

---

### 4. **Activity Log (Start Working)**
When you're ready to work on a task, click the arrow button to move it to the activity log.

**API Endpoints:**
- `GET /api/activity-log/active/` - Get currently active task
- `POST /api/activity-log/{id}/stop/` - Stop task (with completion status)
- `GET /api/activity-log/my_logs/` - Get your activity logs
- `GET /api/activity-log/statistics/` - Get statistics

**Example Start Activity (Click Arrow):**
```json
POST /api/today-plan/5/move_to_activity_log/
Response:
{
  "message": "Activity started successfully",
  "activity_log": {
    "id": 1,
    "today_plan": 5,
    "user": 1,
    "actual_start_time": "2026-02-07T09:05:00Z",
    "status": "IN_PROGRESS",
    "hours_worked": 0,
    "minutes_worked": 0
  }
}
```

---

### 5. **Stop Task (Completion Dialog)**
When you stop a task, you'll be asked if it's completed or still pending.

**Option A: Task Completed**
```json
POST /api/activity-log/1/stop/
{
  "is_completed": true,
  "work_notes": "Successfully implemented login and registration APIs"
}

Response:
{
  "message": "Task completed successfully!",
  "activity_log": {
    "id": 1,
    "status": "COMPLETED",
    "hours_worked": 3.5,
    "minutes_worked": 210,
    "is_task_completed": true
  }
}
```

**Option B: Task Still Pending**
```json
POST /api/activity-log/1/stop/
{
  "is_completed": false,
  "minutes_left": 60,
  "reason": "Need more time to complete testing",
  "work_notes": "Completed 80%, testing remains"
}

Response:
{
  "message": "Task moved to pending. Please replan or complete it later.",
  "activity_log": {
    "id": 1,
    "status": "STOPPED",
    "hours_worked": 2.5,
    "minutes_worked": 150
  },
  "pending": {
    "id": 1,
    "today_plan": 5,
    "original_plan_date": "2026-02-07",
    "minutes_left": 60,
    "status": "PENDING"
  }
}
```

---

### 6. **Pending Section**
Tasks that weren't completed are moved to the pending section.

**API Endpoints:**
- `GET /api/pending/my_pending/` - Get your pending tasks
- `POST /api/pending/{id}/replan/` - Replan a pending task

**Example Replan Task:**
```json
POST /api/pending/1/replan/
{
  "replanned_date": "2026-02-08"
}

Response:
{
  "message": "Task replanned successfully",
  "pending": {
    "id": 1,
    "replanned_date": "2026-02-08",
    "status": "REPLANNED"
  }
}
```

---

### 7. **End Your Day**
At the end of the day, end your session to get a summary.

```json
POST /api/day-session/end_day/
Response:
{
  "message": "Day ended successfully! Great work!",
  "session": {
    "id": 1,
    "ended_at": "2026-02-07T18:00:00Z",
    "is_active": false
  },
  "summary": {
    "completed_tasks": 4,
    "pending_tasks": 1,
    "total_hours_worked": 7.5
  }
}
```

---

## 🔄 Complete Workflow Example

### Morning (9:00 AM)
```bash
# 1. Start your day
POST /api/day-session/start_day/

# 2. Check today's plan
GET /api/today-plan/today/

# 3. Start first task (click arrow)
POST /api/today-plan/1/move_to_activity_log/
```

### During Work (11:00 AM)
```bash
# 4. Stop current task (completed)
POST /api/activity-log/1/stop/
{
  "is_completed": true,
  "work_notes": "Task completed successfully"
}

# 5. Start next task
POST /api/today-plan/2/move_to_activity_log/
```

### Afternoon (3:00 PM)
```bash
# 6. Stop task (not completed)
POST /api/activity-log/2/stop/
{
  "is_completed": false,
  "minutes_left": 30,
  "reason": "Needs more research"
}

# 7. Check pending tasks
GET /api/pending/my_pending/

# 8. Replan for tomorrow
POST /api/pending/1/replan/
{
  "replanned_date": "2026-02-08"
}
```

### Evening (6:00 PM)
```bash
# 9. End your day
POST /api/day-session/end_day/

# 10. View statistics
GET /api/activity-log/statistics/
```

---

## 📊 Statistics and Reports

### Activity Statistics
```bash
GET /api/activity-log/statistics/?start_date=2026-02-01&end_date=2026-02-07
```

Response:
```json
{
  "total_tasks": 25,
  "total_hours": 42.5,
  "total_minutes": 2550,
  "avg_hours_per_task": 1.7,
  "completed_tasks": 22,
  "incomplete_tasks": 3
}
```

---

## 🎨 Frontend Implementation Tips

### Drag & Drop UI
```javascript
// Catalog Section (Draggable)
<div draggable="true" onDragStart={handleDragStart}>
  {catalog.name}
</div>

// Today's Plan (Drop Zone)
<div onDrop={handleDrop} onDragOver={handleDragOver}>
  {/* Dropped items will appear here */}
</div>

// Handle Drop
async function handleDrop(e) {
  const catalogId = e.dataTransfer.getData('catalogId');
  await fetch('/api/today-plan/add_from_catalog/', {
    method: 'POST',
    body: JSON.stringify({
      catalog_id: catalogId,
      plan_date: today,
      scheduled_start_time: '09:00:00',
      scheduled_end_time: '10:00:00',
      planned_duration_minutes: 60
    })
  });
}
```

### Activity Tracker UI
```javascript
// Arrow Button (Start Activity)
async function startActivity(planId) {
  const response = await fetch(`/api/today-plan/${planId}/move_to_activity_log/`, {
    method: 'POST'
  });
  // Show timer UI
}

// Stop Button Dialog
async function stopActivity(activityId, isCompleted) {
  const response = await fetch(`/api/activity-log/${activityId}/stop/`, {
    method: 'POST',
    body: JSON.stringify({
      is_completed: isCompleted,
      minutes_left: isCompleted ? 0 : minutesLeft,
      work_notes: workNotes,
      reason: isCompleted ? '' : reason
    })
  });
  
  if (!isCompleted) {
    // Show in pending section
    showInPendingSection(response.data.pending);
  }
}
```

---

## 🔐 Permissions

### Role-Based Access:
- **ADMIN**: Can see all data across all users
- **MANAGER/TEAMLEAD**: Can see their own data + their department's data
- **EMPLOYEE**: Can only see their own data

---

## ✅ Testing Checklist

1. ✅ Create catalog items
2. ✅ Drag items to today's plan
3. ✅ Set time for each task
4. ✅ Start day session
5. ✅ Click arrow to move to activity log
6. ✅ Stop task (mark as completed)
7. ✅ Stop task (mark as pending)
8. ✅ Replan pending tasks
9. ✅ End day session
10. ✅ View statistics

---

## 🚀 Quick Start

```bash
# 1. Create a catalog item
curl -X POST http://localhost:8000/api/catalog/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Complete Backend API",
    "catalog_type": "PROJECT",
    "estimated_hours": 4
  }'

# 2. Add to today's plan
curl -X POST http://localhost:8000/api/today-plan/add_from_catalog/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "catalog_id": 1,
    "scheduled_start_time": "09:00:00",
    "scheduled_end_time": "13:00:00"
  }'

# 3. Start your day
curl -X POST http://localhost:8000/api/day-session/start_day/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. Start working on first task
curl -X POST http://localhost:8000/api/today-plan/1/move_to_activity_log/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📝 Database Models Summary

1. **Catalog** - Master list of all work items
2. **TodayPlan** - Daily scheduled items with times
3. **ActivityLog** - Actual work tracking with time calculations
4. **Pending** - Incomplete tasks needing replanning
5. **DaySession** - Daily work session tracking

---

## 🎉 All Systems Ready!

Your DAS project is now fully configured with the complete drag-and-drop workflow. Start building your frontend to leverage these powerful APIs!

**Need help?** Check the code comments or run:
```bash
python manage.py show_urls
```
