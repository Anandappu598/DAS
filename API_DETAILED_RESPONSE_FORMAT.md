# Updated API Response Format - Detailed Task Breakdown

## Changes Made

The API now returns **detailed task-by-task breakdown** for both planned and actual work, separating them into planned vs unplanned categories.

---

## **New Response Format - Daily Performance**

### **BEFORE (Old Format)**
```json
{
  "planned": {
    "total_planned_hours": 8.5,
    "planned_tasks": [1, 2, 3, 4],
    "unplanned_tasks_in_plan": [5]
  },
  "actual": {
    "total_hours_worked": 6.75,
    "completed_tasks": 3
  }
}
```

### **AFTER (New Detailed Format)**
```json
{
  "date": "2024-04-07",
  "user": "user@example.com",
  
  "planned": {
    "total_tasks": 5,
    "total_planned_hours": 8.5,
    "total_planned_minutes": 510,
    
    "planned_tasks": {
      "count": 4,
      "total_hours": 7.5,
      "total_minutes": 450,
      "tasks": [
        {
          "id": 1,
          "name": "API Development",
          "planned_minutes": 120,
          "planned_hours": 2.0,
          "status": "COMPLETED",
          "quadrant": "Q1",
          "notes": "Backend endpoints"
        },
        {
          "id": 2,
          "name": "Frontend UI",
          "planned_minutes": 180,
          "planned_hours": 3.0,
          "status": "IN_ACTIVITY",
          "quadrant": "Q1",
          "notes": "Dashboard design"
        },
        {
          "id": 3,
          "name": "Testing",
          "planned_minutes": 90,
          "planned_hours": 1.5,
          "status": "COMPLETED",
          "quadrant": "Q2",
          "notes": "Unit tests"
        },
        {
          "id": 4,
          "name": "Documentation",
          "planned_minutes": 60,
          "planned_hours": 1.0,
          "status": "PLANNED",
          "quadrant": "Q2",
          "notes": null
        }
      ]
    },
    
    "unplanned_tasks": {
      "count": 1,
      "total_hours": 1.0,
      "total_minutes": 60,
      "tasks": [
        {
          "id": 5,
          "name": "Bug Fix",
          "planned_minutes": 60,
          "planned_hours": 1.0,
          "status": "COMPLETED",
          "quadrant": "Q3",
          "notes": "Critical bug in login"
        }
      ]
    },
    
    "quadrant_breakdown": {
      "Q1": {
        "name": "Q1: Do First (Urgent & Important)",
        "count": 2,
        "planned_minutes": 300
      },
      "Q2": {
        "name": "Q2: Schedule (Important, Not Urgent)",
        "count": 2,
        "planned_minutes": 150
      },
      "Q3": {
        "name": "Q3: Delegate (Urgent, Not Important)",
        "count": 1,
        "planned_minutes": 60
      }
    },
    
    "status_breakdown": {
      "COMPLETED": { "name": "Completed", "count": 2 },
      "IN_ACTIVITY": { "name": "In Activity", "count": 1 },
      "PLANNED": { "name": "Planned", "count": 1 }
    }
  },
  
  "actual": {
    "total_hours_worked": 6.75,
    "total_minutes_worked": 405,
    "extra_minutes_worked": 0,
    "extra_hours_worked": 0.0,
    
    "planned_work": {
      "count": 4,
      "total_hours": 5.92,
      "total_minutes": 355,
      "tasks": [
        {
          "id": 1,
          "name": "API Development",
          "planned_minutes": 120,
          "planned_hours": 2.0,
          "actual_minutes": 135,
          "actual_hours": 2.25,
          "status": "COMPLETED",
          "activity_sessions": 2,
          "completed": true
        },
        {
          "id": 2,
          "name": "Frontend UI",
          "planned_minutes": 180,
          "planned_hours": 3.0,
          "actual_minutes": 95,
          "actual_hours": 1.58,
          "status": "IN_ACTIVITY",
          "activity_sessions": 1,
          "completed": false
        },
        {
          "id": 3,
          "name": "Testing",
          "planned_minutes": 90,
          "planned_hours": 1.5,
          "actual_minutes": 85,
          "actual_hours": 1.42,
          "status": "COMPLETED",
          "activity_sessions": 1,
          "completed": true
        },
        {
          "id": 4,
          "name": "Documentation",
          "planned_minutes": 60,
          "planned_hours": 1.0,
          "actual_minutes": 40,
          "actual_hours": 0.67,
          "status": "PLANNED",
          "activity_sessions": 0,
          "completed": false
        }
      ]
    },
    
    "unplanned_work": {
      "count": 1,
      "total_hours": 0.83,
      "total_minutes": 50,
      "tasks": [
        {
          "id": 5,
          "name": "Bug Fix",
          "planned_minutes": 60,
          "planned_hours": 1.0,
          "actual_minutes": 50,
          "actual_hours": 0.83,
          "status": "COMPLETED",
          "activity_sessions": 1,
          "completed": true
        }
      ]
    },
    
    "completed_tasks": 3,
    "in_progress_tasks": 1,
    "not_started_tasks": 1,
    "total_activity_logs": 5
  },
  
  "metrics": {
    "task_completion_rate": 60.0,
    "time_efficiency_percentage": 79.41,
    "hour_difference": -1.75,
    "minute_difference": -105,
    "planned_vs_actual": {
      "planned": 8.5,
      "actual": 6.75,
      "difference": -1.75
    },
    "task_breakdown": {
      "total": 5,
      "completed": 3,
      "in_progress": 1,
      "not_started": 1,
      "planned": 4,
      "unplanned": 1
    },
    "status": "On Track"
  },
  
  "tasks": [...]  // Existing detailed task list
}
```

---

## **New Fields Explanation**

### **Planned Summary Structure**

```
planned:
├─ total_tasks: 5
├─ total_planned_hours: 8.5
├─ total_planned_minutes: 510
│
├─ planned_tasks:                    ← Planned tasks only
│  ├─ count: 4
│  ├─ total_hours: 7.5               ← Total hours of planned tasks
│  ├─ total_minutes: 450
│  └─ tasks:                         ← List of planned tasks with details
│     └─ [task1, task2, task3, ...]
│
├─ unplanned_tasks:                  ← Unplanned tasks only
│  ├─ count: 1
│  ├─ total_hours: 1.0               ← Total hours of unplanned tasks
│  ├─ total_minutes: 60
│  └─ tasks:                         ← List of unplanned tasks with details
│     └─ [task5]
│
├─ quadrant_breakdown: {...}
└─ status_breakdown: {...}
```

### **Actual Summary Structure**

```
actual:
├─ total_hours_worked: 6.75
├─ total_minutes_worked: 405
├─ extra_minutes_worked: 0
├─ extra_hours_worked: 0.0
│
├─ planned_work:                     ← Work done on planned tasks
│  ├─ count: 4
│  ├─ total_hours: 5.92              ← Actual hours on planned tasks
│  ├─ total_minutes: 355
│  └─ tasks:                         ← Planned tasks with actual hours worked
│     └─ [{
│        "name": "API Development",
│        "planned_minutes": 120,
│        "actual_minutes": 135,      ← Actual time spent
│        "completed": true
│     }, ...]
│
├─ unplanned_work:                   ← Work done on unplanned tasks
│  ├─ count: 1
│  ├─ total_hours: 0.83              ← Actual hours on unplanned tasks
│  ├─ total_minutes: 50
│  └─ tasks:                         ← Unplanned tasks with actual hours
│     └─ [{
│        "name": "Bug Fix",
│        "planned_minutes": 60,
│        "actual_minutes": 50,
│        "completed": true
│     }]
│
├─ completed_tasks: 3
├─ in_progress_tasks: 1
├─ not_started_tasks: 1
└─ total_activity_logs: 5
```

---

## **Usage Examples**

### **React Component - Show Breakdown**

```jsx
const performanceData = {
  planned,
  actual,
  metrics
};

// Display Planned Tasks Breakdown
<div>
  <h3>Planned Tasks</h3>
  <p>{planned.planned_tasks.count} tasks - {planned.planned_tasks.total_hours}h total</p>
  {planned.planned_tasks.tasks.map(task => (
    <div key={task.id}>
      <p>{task.name}: {task.planned_hours}h ({task.status})</p>
    </div>
  ))}
</div>

// Display Unplanned Tasks Breakdown
<div>
  <h3>Unplanned Tasks</h3>
  <p>{planned.unplanned_tasks.count} tasks - {planned.unplanned_tasks.total_hours}h total</p>
  {planned.unplanned_tasks.tasks.map(task => (
    <div key={task.id}>
      <p>{task.name}: {task.planned_hours}h ({task.status})</p>
    </div>
  ))}
</div>

// Display Actual Work Breakdown
<div>
  <h3>Actual Work Done</h3>
  
  <h4>Planned Tasks Work</h4>
  <p>{actual.planned_work.count} tasks - {actual.planned_work.total_hours}h worked</p>
  {actual.planned_work.tasks.map(task => (
    <div key={task.id}>
      <p>{task.name}:</p>
      <p>Planned: {task.planned_hours}h | Actual: {task.actual_hours}h</p>
    </div>
  ))}
  
  <h4>Unplanned Tasks Work</h4>
  <p>{actual.unplanned_work.count} tasks - {actual.unplanned_work.total_hours}h worked</p>
  {actual.unplanned_work.tasks.map(task => (
    <div key={task.id}>
      <p>{task.name}:</p>
      <p>Planned: {task.planned_hours}h | Actual: {task.actual_hours}h</p>
    </div>
  ))}
</div>
```

---

## **Dashboard Display Ideas**

### **Option 1: Side-by-Side Comparison Cards**

```
┌─────────────────────────────────────────────────────────┐
│            PLANNED vs ACTUAL - DETAILED BREAKDOWN       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  PLANNED TASKS                                          │
│  ├─ Count: 4 tasks                                      │
│  ├─ Total Planned Hours: 7.5h                           │
│  └─ Tasks:                                              │
│     • API Development: 2.0h [COMPLETED]                 │
│     • Frontend UI: 3.0h [IN ACTIVITY]                   │
│     • Testing: 1.5h [COMPLETED]                         │
│     • Documentation: 1.0h [PLANNED]                     │
│                                                         │
│  UNPLANNED TASKS                                        │
│  ├─ Count: 1 task                                       │
│  ├─ Total Planned Hours: 1.0h                           │
│  └─ Tasks:                                              │
│     • Bug Fix: 1.0h [COMPLETED]                         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ACTUAL WORK DONE                                       │
│  ├─ Total Hours: 6.75h                                  │
│                                                         │
│  On Planned Tasks: 5.92h (70% of total)                │
│  ├─ API Development: 2.25h (planned 2.0h) +15 min      │
│  ├─ Frontend UI: 1.58h (planned 3.0h) -1h 22min        │
│  ├─ Testing: 1.42h (planned 1.5h) -3 min               │
│  └─ Documentation: 0.67h (planned 1.0h) -20 min        │
│                                                         │
│  On Unplanned Tasks: 0.83h (12% of total)              │
│  └─ Bug Fix: 0.83h (planned 1.0h) -10 min              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### **Option 2: Doughnut Chart with Breakdown**

```
Planned Tasks Breakdown:
        Q1  Q2  Planned: 7.5h
        │   │   ┌─────────────┐
       /     \  / API Dev: 2h \
      / 60%   \/  Frontend: 3h \
     |  ┌──┐  /  Testing: 1.5h  \
     |  │  │ \  Docs: 1.0h      /
     |  └──┘  \─────────────────/
      \   /    
       \ /   
        Q3

Unplanned Tasks:
        ┌─────────────┐
       /  Unplanned  \
      / Tasks: 1.0h  \
     |  Bug Fix: 1h  |
      \             /
       \───────────/

Actual Work Breakdown:
        Planned: 5.92h (88%)
        ┌────────────────┐
       /  Actual Work   \
      / Total: 6.75h    \
     |  Unplanned: 0.83h|
      \                /
       \──────────────/
```

---

## **API Endpoints (No Changes)**

All endpoints remain the same:
- `GET /api/daily-performance/`
- `GET /api/daily-performance/<date>/`
- `GET /api/daily-performance/range/<start>/<end>/`
- `GET /api/weekly-comparison/`
- `GET /api/monthly-comparison/`
- `GET /api/performance-dashboard/`

---

## **What's Improved**

✅ **Detailed Task Lists** - See every task with hours instead of just IDs  
✅ **Planned vs Unplanned Separation** - Clear distinction in both planned and actual  
✅ **Activity Sessions** - Know how many times user worked on each task  
✅ **Completion Status** - See which tasks are actually completed  
✅ **Better Analysis** - Calculate time variance (planned vs actual) easily  
✅ **Task Names** - Get task names directly without separate lookup  
✅ **Work Distribution** - See percentage of time on planned vs unplanned  

---

