# Actual API Responses - All 3 Endpoints

## 1. GET /api/daily-performance/ → TODAY'S DATA

**Date:** 2026-04-08 (Today)

**Response:**
```json
{
  "date": "2026-04-08",
  "user": "athirupan@meridatechminds.com",
  "planned_summary": {
    "daily_plan": {
      "date": "2026-04-08",
      "planned_hours": null,
      "has_daily_planner": false
    },
    "total_tasks": 0,
    "total_planned_hours": 0.0,
    "total_planned_minutes": 0,
    "planned_tasks": {
      "count": 0,
      "total_hours": 0.0,
      "total_minutes": 0,
      "tasks": []
    },
    "unplanned_tasks": {
      "count": 0,
      "total_hours": 0.0,
      "total_minutes": 0,
      "tasks": []
    },
    "quadrant_breakdown": {
      "Q1": {
        "name": "Q1: Do First (Urgent & Important)",
        "count": 0,
        "planned_minutes": 0
      },
      "Q2": {
        "name": "Q2: Schedule (Important, Not Urgent)",
        "count": 0,
        "planned_minutes": 0
      },
      "Q3": {
        "name": "Q3: Delegate (Urgent, Not Important)",
        "count": 0,
        "planned_minutes": 0
      },
      "Q4": {
        "name": "Q4: Eliminate (Not Urgent, Not Important)",
        "count": 0,
        "planned_minutes": 0
      }
    },
    "status_breakdown": {
      "PLANNED": {"name": "Planned", "count": 0},
      "STARTED": {"name": "Started", "count": 0},
      "IN_ACTIVITY": {"name": "In Activity Log", "count": 0},
      "COMPLETED": {"name": "Completed", "count": 0},
      "MOVED_TO_PENDING": {"name": "Moved to Pending", "count": 0}
    }
  },
  "actual_summary": {
    "total_hours_worked": 0.0,
    "total_minutes_worked": 0,
    "extra_minutes_worked": 0,
    "extra_hours_worked": 0.0,
    "planned_work": {
      "count": 0,
      "total_hours": 0.0,
      "total_minutes": 0,
      "tasks": []
    },
    "unplanned_work": {
      "count": 0,
      "total_hours": 0.0,
      "total_minutes": 0,
      "tasks": []
    },
    "completed_tasks": 0,
    "in_progress_tasks": 0,
    "not_started_tasks": 0,
    "total_activity_logs": 0
  },
  "metrics": {
    "task_completion_rate": 0,
    "time_efficiency_percentage": 0,
    "hour_difference": 0.0,
    "minute_difference": 0,
    "planned_vs_actual": {
      "planned": 0.0,
      "actual": 0.0,
      "difference": 0.0
    },
    "task_breakdown": {
      "total": 0,
      "completed": 0,
      "in_progress": 0,
      "not_started": 0,
      "planned": 0,
      "unplanned": 0
    },
    "status": "Needs Attention"
  },
  "tasks": []
}
```

---

## 2. GET /api/daily-performance/<date>/ → SPECIFIC DATE

**Date:** 2026-04-07 (Specific Date)

**Response:** (Same structure as endpoint 1)
```json
{
  "date": "2026-04-07",
  "user": "athirupan@meridatechminds.com",
  "planned_summary": {
    "daily_plan": {
      "date": "2026-04-07",
      "planned_hours": null,
      "has_daily_planner": false
    },
    "total_tasks": 0,
    "total_planned_hours": 0.0,
    "total_planned_minutes": 0,
    "planned_tasks": {
      "count": 0,
      "total_hours": 0.0,
      "total_minutes": 0,
      "tasks": []
    },
    "unplanned_tasks": {
      "count": 0,
      "total_hours": 0.0,
      "total_minutes": 0,
      "tasks": []
    },
    "quadrant_breakdown": {
      "Q1": {"name": "Q1: Do First (Urgent & Important)", "count": 0, "planned_minutes": 0},
      "Q2": {"name": "Q2: Schedule (Important, Not Urgent)", "count": 0, "planned_minutes": 0},
      "Q3": {"name": "Q3: Delegate (Urgent, Not Important)", "count": 0, "planned_minutes": 0},
      "Q4": {"name": "Q4: Eliminate (Not Urgent, Not Important)", "count": 0, "planned_minutes": 0}
    },
    "status_breakdown": {
      "PLANNED": {"name": "Planned", "count": 0},
      "STARTED": {"name": "Started", "count": 0},
      "IN_ACTIVITY": {"name": "In Activity Log", "count": 0},
      "COMPLETED": {"name": "Completed", "count": 0},
      "MOVED_TO_PENDING": {"name": "Moved to Pending", "count": 0}
    }
  },
  "actual_summary": {
    "total_hours_worked": 0.0,
    "total_minutes_worked": 0,
    "extra_minutes_worked": 0,
    "extra_hours_worked": 0.0,
    "planned_work": {
      "count": 0,
      "total_hours": 0.0,
      "total_minutes": 0,
      "tasks": []
    },
    "unplanned_work": {
      "count": 0,
      "total_hours": 0.0,
      "total_minutes": 0,
      "tasks": []
    },
    "completed_tasks": 0,
    "in_progress_tasks": 0,
    "not_started_tasks": 0,
    "total_activity_logs": 0
  },
  "metrics": {
    "task_completion_rate": 0,
    "time_efficiency_percentage": 0,
    "hour_difference": 0.0,
    "minute_difference": 0,
    "planned_vs_actual": {
      "planned": 0.0,
      "actual": 0.0,
      "difference": 0.0
    },
    "task_breakdown": {
      "total": 0,
      "completed": 0,
      "in_progress": 0,
      "not_started": 0,
      "planned": 0,
      "unplanned": 0
    },
    "status": "Needs Attention"
  },
  "tasks": []
}
```

---

## 3. GET /api/daily-performance/range/<start>/<end>/ → DATE RANGE

**Range:** 2026-04-05 to 2026-04-09 (5 days)

**Response:**
```json
{
  "start_date": "2026-04-05",
  "end_date": "2026-04-09",
  "days_count": 5,
  "daily_data": [
    {
      "date": "2026-04-05",
      "user": "athirupan@meridatechminds.com",
      "planned_summary": {
        "daily_plan": {
          "date": "2026-04-05",
          "planned_hours": null,
          "has_daily_planner": false
        },
        "total_tasks": 0,
        "total_planned_hours": 0.0,
        "total_planned_minutes": 0,
        "planned_tasks": {
          "count": 0,
          "total_hours": 0.0,
          "total_minutes": 0,
          "tasks": []
        },
        "unplanned_tasks": {
          "count": 0,
          "total_hours": 0.0,
          "total_minutes": 0,
          "tasks": []
        }
      },
      "actual_summary": {
        "total_hours_worked": 0.0,
        "total_minutes_worked": 0,
        "planned_work": {
          "count": 0,
          "total_hours": 0.0,
          "total_minutes": 0,
          "tasks": []
        },
        "unplanned_work": {
          "count": 0,
          "total_hours": 0.0,
          "total_minutes": 0,
          "tasks": []
        }
      },
      "metrics": {
        "task_completion_rate": 0,
        "time_efficiency_percentage": 0,
        "hour_difference": 0.0,
        "minute_difference": 0
      }
    },
    // ... same structure for 2026-04-06, 2026-04-07, 2026-04-08, 2026-04-09
  ]
}
```

---

## Response Structure Breakdown

### Top Level Fields
```
{
  "date": "2026-04-08",                    ← Date of data
  "user": "athirupan@meridatechminds.com", ← User email
  "planned_summary": {...},                ← What was PLANNED
  "actual_summary": {...},                 ← What was ACTUALLY DONE
  "metrics": {...},                        ← Summary metrics
  "tasks": []                              ← Array of tasks
}
```

### planned_summary Section
```
"planned_summary": {
  "daily_plan": {                          ← Daily target from DailyPlanner
    "date": "2026-04-08",
    "planned_hours": null,                 ← Target hours (null if no plan)
    "has_daily_planner": false             ← Boolean flag
  },
  
  "total_tasks": 0,                        ← Count of all tasks
  "total_planned_hours": 0.0,              ← Sum of all task hours
  "total_planned_minutes": 0,
  
  "planned_tasks": {                       ← Tasks marked as PLANNED
    "count": 0,
    "total_hours": 0.0,
    "total_minutes": 0,
    "tasks": [
      {
        "id": 1,
        "name": "Task Name",
        "planned_hours": 2.0,
        "planned_minutes": 120,
        "status": "COMPLETED",
        "quadrant": "Q1",
        "notes": "..."
      }
    ]
  },
  
  "unplanned_tasks": {                     ← Tasks marked as UNPLANNED
    "count": 0,
    "total_hours": 0.0,
    "total_minutes": 0,
    "tasks": [...]
  },
  
  "quadrant_breakdown": {                  ← Time by urgency/importance
    "Q1": {"name": "Do First", "count": 0, "planned_minutes": 0},
    "Q2": {"name": "Schedule", "count": 0, "planned_minutes": 0},
    "Q3": {"name": "Delegate", "count": 0, "planned_minutes": 0},
    "Q4": {"name": "Eliminate", "count": 0, "planned_minutes": 0}
  },
  
  "status_breakdown": {                    ← Tasks by status
    "PLANNED": {"name": "Planned", "count": 0},
    "STARTED": {"name": "Started", "count": 0},
    "IN_ACTIVITY": {"name": "In Activity Log", "count": 0},
    "COMPLETED": {"name": "Completed", "count": 0},
    "MOVED_TO_PENDING": {"name": "Moved to Pending", "count": 0}
  }
}
```

### actual_summary Section
```
"actual_summary": {
  "total_hours_worked": 0.0,               ← Total time logged
  "total_minutes_worked": 0,
  "extra_minutes_worked": 0,               ← Extra time beyond plan
  "extra_hours_worked": 0.0,
  
  "planned_work": {                        ← Time spent on planned tasks
    "count": 0,
    "total_hours": 0.0,
    "total_minutes": 0,
    "tasks": [
      {
        "id": 1,
        "name": "Task Name",
        "planned_hours": 2.0,
        "actual_hours": 2.25,              ← Time actually spent
        "actual_minutes": 135,
        "status": "COMPLETED",
        "completed": true,
        "activity_sessions": 2             ← Number of work sessions
      }
    ]
  },
  
  "unplanned_work": {                      ← Time spent on unplanned tasks
    "count": 0,
    "total_hours": 0.0,
    "total_minutes": 0,
    "tasks": [...]
  },
  
  "completed_tasks": 0,                    ← Status counts
  "in_progress_tasks": 0,
  "not_started_tasks": 0,
  "total_activity_logs": 0                 ← Number of log entries
}
```

### metrics Section
```
"metrics": {
  "task_completion_rate": 0,               ← % of tasks completed
  "time_efficiency_percentage": 0,         ← (actual/planned)*100
  "hour_difference": 0.0,                  ← actual - planned
  "minute_difference": 0,
  
  "planned_vs_actual": {
    "planned": 0.0,
    "actual": 0.0,
    "difference": 0.0
  },
  
  "task_breakdown": {
    "total": 0,
    "completed": 0,
    "in_progress": 0,
    "not_started": 0,
    "planned": 0,
    "unplanned": 0
  },
  
  "status": "Needs Attention"               ← Overall status
}
```

---

## Example Response with DATA

If there were tasks and activity logs, here's what it would look like:

```json
{
  "date": "2026-04-08",
  "user": "athirupan@meridatechminds.com",
  "planned_summary": {
    "daily_plan": {
      "date": "2026-04-08",
      "planned_hours": 8.0,
      "has_daily_planner": true
    },
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
          "planned_hours": 2.0,
          "planned_minutes": 120,
          "status": "COMPLETED",
          "quadrant": "Q1",
          "notes": "Backend endpoints"
        },
        {
          "id": 2,
          "name": "Frontend UI",
          "planned_hours": 3.0,
          "planned_minutes": 180,
          "status": "IN_ACTIVITY",
          "quadrant": "Q1",
          "notes": "Dashboard design"
        },
        {
          "id": 3,
          "name": "Testing",
          "planned_hours": 1.5,
          "planned_minutes": 90,
          "status": "COMPLETED",
          "quadrant": "Q2",
          "notes": null
        },
        {
          "id": 4,
          "name": "Documentation",
          "planned_hours": 1.0,
          "planned_minutes": 60,
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
          "planned_hours": 1.0,
          "planned_minutes": 60,
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
      },
      "Q4": {
        "name": "Q4: Eliminate (Not Urgent, Not Important)",
        "count": 0,
        "planned_minutes": 0
      }
    }
  },
  "actual_summary": {
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
          "planned_hours": 2.0,
          "actual_hours": 2.25,
          "actual_minutes": 135,
          "status": "COMPLETED",
          "completed": true,
          "activity_sessions": 2
        },
        {
          "id": 2,
          "name": "Frontend UI",
          "planned_hours": 3.0,
          "actual_hours": 1.58,
          "actual_minutes": 95,
          "status": "IN_ACTIVITY",
          "completed": false,
          "activity_sessions": 1
        },
        {
          "id": 3,
          "name": "Testing",
          "planned_hours": 1.5,
          "actual_hours": 1.42,
          "actual_minutes": 85,
          "status": "COMPLETED",
          "completed": true,
          "activity_sessions": 1
        },
        {
          "id": 4,
          "name": "Documentation",
          "planned_hours": 1.0,
          "actual_hours": 0.67,
          "actual_minutes": 40,
          "status": "PLANNED",
          "completed": false,
          "activity_sessions": 0
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
          "planned_hours": 1.0,
          "actual_hours": 0.83,
          "actual_minutes": 50,
          "status": "COMPLETED",
          "completed": true,
          "activity_sessions": 1
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
  "tasks": []
}
```

---

## Key Points

1. **daily_plan.planned_hours** → Target hours the user set (from DailyPlanner model)
2. **daily_plan.has_daily_planner** → Boolean: was a plan set for this day?
3. **planned_tasks** → Tasks user specifically planned to do
4. **unplanned_tasks** → Tasks added during the day that weren't planned
5. **planned_work** → How much time was actually spent on planned tasks
6. **unplanned_work** → How much time was actually spent on unplanned tasks
7. **metrics** → Overall performance indicators

---

## Date Range Response

For the date range endpoint, the response is an array wrapper:

```json
{
  "start_date": "2026-04-05",
  "end_date": "2026-04-09",
  "days_count": 5,
  "daily_data": [
    { /* Full response for 2026-04-05 */ },
    { /* Full response for 2026-04-06 */ },
    { /* Full response for 2026-04-07 */ },
    { /* Full response for 2026-04-08 */ },
    { /* Full response for 2026-04-09 */ }
  ]
}
```

Each item in `daily_data` contains the complete single-day response structure.

