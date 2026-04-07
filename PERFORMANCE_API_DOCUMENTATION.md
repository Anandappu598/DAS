# Planned vs Achieved API Documentation

## Overview
This API provides comprehensive analysis of planned work vs actual work done. It compares tasks from **TodayPlan** (planned) with **ActivityLog** (actual work).

---

## **Data Structure**

### TodayPlan (Planned)
- Tasks user plans to work on
- Contains planned_duration_minutes
- Has quadrant classification (Q1/Q2/Q3/Q4)
- Can be PLANNED (from catalog) or UNPLANNED (dragged directly)

### ActivityLog (Actual)
- Records actual work done when user starts/stops a task
- Tracks: actual_start_time, actual_end_time, minutes_worked
- Can have multiple logs per task (multiple sessions)
- Marks tasks as completed or pending

---

## **API Endpoints**

### 1. **Daily Performance** 
Get planned vs achieved for a specific date

#### Request
```
GET /api/daily-performance/
GET /api/daily-performance/2024-04-07/
```

#### Response
```json
{
  "date": "2024-04-07",
  "user": "user@example.com",
  "planned": {
    "total_tasks": 5,
    "total_planned_hours": 8.5,
    "total_planned_minutes": 510,
    "quadrant_breakdown": {
      "Q1": {
        "name": "Q1: Do First (Urgent & Important)",
        "count": 2,
        "planned_minutes": 240
      },
      "Q2": {
        "name": "Q2: Schedule (Important, Not Urgent)",
        "count": 2,
        "planned_minutes": 180
      },
      "Q3": {
        "name": "Q3: Delegate (Urgent, Not Important)",
        "count": 1,
        "planned_minutes": 90
      }
    },
    "status_breakdown": {
      "PLANNED": { "name": "Planned", "count": 1 },
      "STARTED": { "name": "Started", "count": 2 },
      "COMPLETED": { "name": "Completed", "count": 2 }
    },
    "planned_tasks": [1, 2, 3, 4],
    "unplanned_tasks_in_plan": [5]
  },
  
  "actual": {
    "total_hours_worked": 6.75,
    "total_minutes_worked": 405,
    "extra_minutes_worked": 0,
    "extra_hours_worked": 0.0,
    "completed_tasks": 3,
    "in_progress_tasks": 1,
    "not_started_tasks": 1,
    "unplanned_tasks_count": 1,
    "unplanned_planned_minutes": 90,
    "total_activity_logs": 4
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
  
  "tasks": [
    {
      "id": 1,
      "name": "API Development",
      "planned_minutes": 120,
      "planned_hours": 2.0,
      "quadrant": "Q1",
      "status": "COMPLETED",
      "is_unplanned": false,
      "activity_logs_count": 2,
      "total_worked_minutes": 135,
      "activities": [
        {
          "id": 1,
          "minutes_worked": 70,
          "hours_worked": 1.17,
          "status": "STOPPED",
          "start_time": "2024-04-07T09:00:00Z",
          "end_time": "2024-04-07T10:10:00Z",
          "completed": false
        },
        {
          "id": 2,
          "minutes_worked": 65,
          "hours_worked": 1.08,
          "status": "COMPLETED",
          "start_time": "2024-04-07T11:00:00Z",
          "end_time": "2024-04-07T12:05:00Z",
          "completed": true
        }
      ]
    }
  ]
}
```

---

### 2. **Date Range Performance**
Get daily breakdown for a period

#### Request
```
GET /api/daily-performance/range/2024-04-01/2024-04-07/
```

#### Response
```json
{
  "period": {
    "start_date": "2024-04-01",
    "end_date": "2024-04-07",
    "days": 7
  },
  "user": "user@example.com",
  "daily_breakdown": [
    {
      "date": "2024-04-01",
      "planned_hours": 8.0,
      "actual_hours": 7.5,
      "total_tasks": 5,
      "completed_tasks": 4,
      "completion_rate": 80.0,
      "efficiency": 93.75
    },
    {
      "date": "2024-04-02",
      "planned_hours": 8.5,
      "actual_hours": 8.0,
      "total_tasks": 6,
      "completed_tasks": 5,
      "completion_rate": 83.33,
      "efficiency": 94.12
    }
  ],
  "totals": {
    "total_planned_hours": 58.5,
    "total_actual_hours": 52.75,
    "total_tasks": 42,
    "total_completed": 34,
    "completion_rate": 80.95,
    "average_daily_planned": 8.36,
    "average_daily_actual": 7.54
  }
}
```

---

### 3. **Weekly Comparison**
Compare planned vs achieved for a week

#### Request
```
GET /api/weekly-comparison/
GET /api/weekly-comparison/2024/15/
```
*Year: 2024, Week: 15 (week number in year)*

#### Response
```json
{
  "week": {
    "year": 2024,
    "week_number": 15,
    "start_date": "2024-04-08",
    "end_date": "2024-04-14"
  },
  "user": "user@example.com",
  "daily_breakdown": [
    {
      "date": "2024-04-08",
      "planned_hours": 8.0,
      "actual_hours": 7.8,
      "total_tasks": 5,
      "completed_tasks": 4,
      "completion_rate": 80.0,
      "efficiency": 97.5
    }
  ],
  "weekly_totals": {
    "total_planned_hours": 56.0,
    "total_actual_hours": 54.5,
    "total_completed_tasks": 28,
    "total_tasks": 35,
    "weekly_completion_rate": 80.0
  },
  "weekly_metrics": {
    "average_daily_planned": 8.0,
    "average_daily_actual": 7.79,
    "weekly_efficiency": 97.32,
    "total_extra_hours": 0.0
  }
}
```

---

### 4. **Monthly Comparison**
Compare planned vs achieved for a month

#### Request
```
GET /api/monthly-comparison/
GET /api/monthly-comparison/2024/4/
```

#### Response
```json
{
  "month": {
    "year": 2024,
    "month": 4,
    "start_date": "2024-04-01",
    "end_date": "2024-04-30"
  },
  "user": "user@example.com",
  "weekly_breakdown": [
    {
      "week": "Week 1",
      "planned_hours": 40.0,
      "actual_hours": 38.5,
      "completion_rate": 82.5
    }
  ],
  "monthly_totals": {
    "total_planned_hours": 160.0,
    "total_actual_hours": 155.0,
    "total_completed_tasks": 110,
    "total_tasks": 140,
    "monthly_completion_rate": 78.57
  },
  "monthly_metrics": {
    "average_daily_planned": 5.33,
    "average_daily_actual": 5.17,
    "monthly_efficiency": 96.88,
    "total_extra_hours": 0.0
  }
}
```

---

### 5. **Performance Dashboard**
Comprehensive dashboard with today, week, and month data

#### Request
```
GET /api/performance-dashboard/
```

#### Response
```json
{
  "user": "user@example.com",
  "today": {
    "planned_hours": 8.5,
    "actual_hours": 6.75,
    "completed_tasks": 3,
    "total_tasks": 5,
    "completion_rate": 60.0,
    "efficiency": 79.41,
    "date": "2024-04-07"
  },
  "this_week": {
    "planned_hours": 56.0,
    "actual_hours": 54.5,
    "completed_tasks": 28,
    "total_tasks": 35,
    "completion_rate": 80.0,
    "efficiency": 97.32,
    "start_date": "2024-04-08",
    "end_date": "2024-04-14"
  },
  "this_month": {
    "planned_hours": 160.0,
    "actual_hours": 155.0,
    "completed_tasks": 110,
    "total_tasks": 140,
    "completion_rate": 78.57,
    "efficiency": 96.88,
    "start_date": "2024-04-01",
    "end_date": "2024-04-30"
  },
  "key_insights": {
    "status": "On Track",
    "avg_daily_efficiency_week": 97.32,
    "pending_tasks": 7,
    "overdue_tasks": 0
  }
}
```

---

## **Key Metrics Explained**

| Metric | Formula | Meaning |
|--------|---------|---------|
| **Completion Rate** | (Completed Tasks / Total Tasks) × 100 | % of tasks finished |
| **Time Efficiency** | (Actual Hours / Planned Hours) × 100 | How well you matched plan |
| **Hour Difference** | Actual Hours - Planned Hours | Did you work more/less |
| **Quadrant Breakdown** | Tasks by Eisenhower Matrix | Priority distribution |
| **Status** | Auto-calculated based on completion rate | On Track / Behind Schedule |

---

## **Authentication**
All endpoints require:
```
Authorization: Bearer <token>
```

---

## **Query Parameters**
All endpoints support filtering by:
- `date`: Specific date (YYYY-MM-DD)
- `start_date`, `end_date`: Date range
- `year`, `week`: Week number
- `year`, `month`: Month number

---

## **Error Responses**

### 400 Bad Request
```json
{
  "error": "Invalid date format. Use YYYY-MM-DD"
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

---

