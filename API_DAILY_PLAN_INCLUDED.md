# Updated API - Daily Plan Data Included

## What's New

The API now includes **Daily Planner** data showing:
- Total planned hours for the day (from Daily Planner)
- All tasks that are planned for that day
- Breakdown by planned vs unplanned

---

## **New Response Structure**

```json
{
  "date": "2024-04-07",
  "user": "user@example.com",
  
  "planned": {
    "daily_plan": {
      "date": "2024-04-07",
      "planned_hours": 8.0,        ← Total hours set in daily planner
      "has_daily_planner": true
    },
    
    "total_tasks": 5,
    "total_planned_hours": 8.5,    ← Sum of all tasks
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
  }
}
```

---

## **Key Fields Added**

### **Daily Plan Section**
```json
"daily_plan": {
  "date": "2024-04-07",
  "planned_hours": 8.0,       ← Total hours set in daily planner for the day
  "has_daily_planner": true   ← Whether daily planner entry exists
}
```

**Purpose:**
- Shows the target hours the user set for the day
- Separate from task breakdown (which might sum to different total)
- Allows comparison: target_hours (daily plan) vs scheduled_hours (all tasks)

---

## **Data Breakdown Example**

### **What Daily Plan Shows:**
```
Daily Plan Target: 8.0 hours
(Set by user as their goal for the day)

Planned Tasks: 7.5 hours
├─ API Development: 2.0h
├─ Frontend UI: 3.0h
├─ Testing: 1.5h
└─ Documentation: 1.0h

Unplanned Tasks: 1.0h
└─ Bug Fix: 1.0h

Total Tasks: 8.5h
(More than daily plan target!)
```

### **What Actual Work Shows:**
```
Actual Hours Worked: 6.75h
(Actual time spent)

On Planned Tasks: 5.92h
├─ API Development: 2.25h (planned 2.0h) ↑ +0.25h
├─ Frontend UI: 1.58h (planned 3.0h) ↓ -1.42h
├─ Testing: 1.42h (planned 1.5h) ↓ -0.08h
└─ Documentation: 0.67h (planned 1.0h) ↓ -0.33h

On Unplanned Tasks: 0.83h
└─ Bug Fix: 0.83h (planned 1.0h) ↓ -0.17h
```

---

## **Frontend Usage Example**

### **React Component**

```jsx
const { planned, actual } = apiResponse;

// Show Daily Plan Target
<div className="daily-plan-section">
  <h3>Daily Plan</h3>
  <p>Target Hours: {planned.daily_plan.planned_hours}h</p>
  <p>Date: {planned.daily_plan.date}</p>
</div>

// Show All Planned Tasks
<div className="planned-tasks-section">
  <h4>Planned Tasks ({planned.planned_tasks.count})</h4>
  <p>Total: {planned.planned_tasks.total_hours}h</p>
  
  {planned.planned_tasks.tasks.map(task => (
    <div key={task.id} className="task-item">
      <h5>{task.name}</h5>
      <p>Planned: {task.planned_hours}h | Status: {task.status}</p>
      
      {actual.planned_work.tasks.find(t => t.id === task.id) && (
        <p>Actual: {actual.planned_work.tasks.find(t => t.id === task.id).actual_hours}h</p>
      )}
    </div>
  ))}
</div>

// Show Unplanned Tasks Separately
<div className="unplanned-tasks-section">
  <h4>Unplanned Tasks ({planned.unplanned_tasks.count})</h4>
  <p>Total: {planned.unplanned_tasks.total_hours}h</p>
  
  {planned.unplanned_tasks.tasks.map(task => (
    <div key={task.id} className="task-item">
      <h5>{task.name}</h5>
      <p>Planned: {task.planned_hours}h | Status: {task.status}</p>
      
      {actual.unplanned_work.tasks.find(t => t.id === task.id) && (
        <p>Actual: {actual.unplanned_work.tasks.find(t => t.id === task.id).actual_hours}h</p>
      )}
    </div>
  ))}
</div>

// Show Summary Cards
<div className="summary">
  <Card>
    <h5>Daily Target</h5>
    <p className="large">{planned.daily_plan.planned_hours}h</p>
  </Card>
  
  <Card>
    <h5>Planned Tasks Total</h5>
    <p className="large">{planned.planned_tasks.total_hours}h</p>
  </Card>
  
  <Card>
    <h5>Actual Worked</h5>
    <p className="large">{actual.total_hours_worked}h</p>
  </Card>
</div>
```

---

## **Dashboard Display Suggestions**

### **Option 1: Daily Plan Overview**

```
┌─────────────────────────────────────────┐
│       DAILY PLAN FOR 2024-04-07         │
├─────────────────────────────────────────┤
│                                         │
│  Daily Target Hours: 8.0h               │
│  ├─ Planned Tasks:  7.5h (4 tasks)     │
│  │  ├─ API Development: 2.0h           │
│  │  ├─ Frontend UI: 3.0h               │
│  │  ├─ Testing: 1.5h                   │
│  │  └─ Documentation: 1.0h             │
│  │                                     │
│  └─ Unplanned Tasks: 1.0h (1 task)    │
│     └─ Bug Fix: 1.0h                   │
│                                         │
│  Actual Worked: 6.75h (79% of target) │
│  ├─ Planned Work: 5.92h (88% done)    │
│  └─ Unplanned Work: 0.83h (12% done)  │
│                                         │
└─────────────────────────────────────────┘
```

### **Option 2: Comparison View**

```
DAILY PLAN SUMMARY
═══════════════════════════════════════

Target for Day:    8.0 hours
───────────────────────────
Planned Tasks:     7.5 hours (93.75% of target)
Unplanned Tasks:   1.0 hours (12.5% over target)
Total Scheduled:   8.5 hours (106% of target)
───────────────────────────
Actual Worked:     6.75 hours (84% of target)

COMPLETION SUMMARY
Progress: 60% (3 of 5 tasks completed)
Efficiency: 79% (worked less than planned)
Status: On Track ✓
```

---

## **Example Scenarios**

### **Scenario 1: On Track**
```
Daily Target: 8h
Planned Tasks: 7.5h
Unplanned: 0.5h
Actual Worked: 7.8h ✓ (97.5% efficiency)
```

### **Scenario 2: Over-planned**
```
Daily Target: 8h
Planned Tasks: 10h (125% of target)
Unplanned: 1h
Actual Worked: 7.2h (90% efficiency, but only 60% of tasks done)
→ User took on too much work
```

### **Scenario 3: High Unplanned Work**
```
Daily Target: 8h
Planned Tasks: 5h
Unplanned: 4h (80% of target is unplanned!)
Actual Worked: 8.5h (106% efficiency)
→ User did more unplanned work than planned
```

---

## **Key Metrics to Display**

```
1. Daily Plan Target      → From daily_plan.planned_hours
2. Planned Tasks Total    → From planned_tasks.total_hours
3. Unplanned Tasks Total  → From unplanned_tasks.total_hours
4. Total Scheduled        → planned_tasks + unplanned_tasks
5. Actual Hours Worked    → From actual.total_hours_worked
6. Planned Work Done      → From actual.planned_work.total_hours
7. Unplanned Work Done    → From actual.unplanned_work.total_hours
8. Task Completion Rate   → From metrics.task_completion_rate
9. Time Efficiency        → From metrics.time_efficiency_percentage
```

---

## **Endpoints (No Change)**

All endpoints now return the new format with daily plan data:

```
GET /api/daily-performance/
GET /api/daily-performance/<date>/
GET /api/daily-performance/range/<start>/<end>/
GET /api/weekly-comparison/
GET /api/monthly-comparison/
GET /api/performance-dashboard/
```

---

