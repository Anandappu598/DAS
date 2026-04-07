# System Architecture & Data Flow Diagrams

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React/Flutter)                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ Dashboard Page   │  │ Daily View       │  │ Weekly View  │  │
│  │ Performance Card │  │ Progress Bars    │  │ Line Chart   │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
│           │                     │                      │          │
└───────────┼─────────────────────┼──────────────────────┼──────────┘
            │                     │                      │
            ▼                     ▼                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                    REST API ENDPOINTS                             │
│                                                                   │
│  GET /api/daily-performance/          (Today's data)             │
│  GET /api/daily-performance/<date>/    (Specific day)            │
│  GET /api/daily-performance/range/     (Date range)              │
│  GET /api/weekly-comparison/           (This week)               │
│  GET /api/monthly-comparison/          (This month)              │
│  GET /api/performance-dashboard/       (Overview)                │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
            │                     │                      │
            ▼                     ▼                      ▼
┌──────────────────────────────────────────────────────────────────┐
│        DATA SERIALIZERS & VIEWS (Django REST Framework)          │
│                                                                   │
│  DailyPerformanceSerializer     ← Processes daily data           │
│  WeeklyComparisonSerializer     ← Processes weekly data          │
│  MonthlyComparisonSerializer    ← Processes monthly data         │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
            │                     │                      │
            ▼                     ▼                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                      DATABASE MODELS                              │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  TodayPlan   │  │ ActivityLog  │  │  DailyPlanner        │   │
│  ├──────────────┤  ├──────────────┤  ├──────────────────────┤   │
│  │ user         │  │ user         │  │ user                 │   │
│  │ plan_date    │  │ today_plan   │  │ date                 │   │
│  │ planned_dura-│  │ actual_start │  │ planned_hours        │   │
│  │   tion_mins  │  │ actual_end   │  │ actual_hours         │   │
│  │ status       │  │ minutes_work │  └──────────────────────┘   │
│  │ quadrant     │  │ is_completed │                              │
│  │ is_unplanned │  └──────────────┘                              │
│  └──────────────┘                                                 │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow - Daily Performance Request

```
User Opens Dashboard
        │
        ▼
Frontend Component Mounts
        │
        ├─→ useEffect Hook Triggered
        │
        ▼
performanceAPI.getDailyPerformance()
        │
        ├─→ GET /api/daily-performance/
        ├─→ Header: Authorization: Bearer TOKEN
        │
        ▼
Django URL Router
        │
        ├─→ Matches Path: /api/daily-performance/
        └─→ Routes to: DailyPerformanceView.get()
        │
        ▼
DailyPerformanceView.get()
        │
        ├─→ Get Current User
        ├─→ Get date (today if not specified)
        │
        ▼
Query Database
        │
        ├─→ TodayPlan.objects.filter(user=user, plan_date=date)
        │   └─→ Get all planned tasks for today
        │
        ├─→ ActivityLog.objects.filter(user=user, plan_date=date)
        │   └─→ Get all actual work logged for today
        │
        ▼
Process Data with Serializer
        │
        ├─→ Calculate planned summary
        │   ├─ Total tasks: 5
        │   ├─ Total planned hours: 8.5
        │   └─ Quadrant breakdown
        │
        ├─→ Calculate actual summary
        │   ├─ Total worked: 6.75h
        │   ├─ Completed: 3
        │   └─ Unplanned: 1
        │
        ├─→ Calculate metrics
        │   ├─ Completion rate: (3/5)*100 = 60%
        │   ├─ Efficiency: (6.75/8.5)*100 = 79.41%
        │   └─ Status: On Track
        │
        ▼
Return JSON Response
        │
        ├─→ HTTP 200 OK
        ├─→ Body: {planned, actual, metrics, tasks}
        │
        ▼
Frontend Receives Response
        │
        ├─→ Store in State (React) / Provider (Flutter)
        ├─→ Update UI Components
        │
        ▼
Display on Dashboard
        │
        ├─→ Show Daily Performance Card
        ├─→ Display Progress Bars
        ├─→ Render Pie Chart
        └─→ Show metrics with colors
```

---

## 📈 Data Transformation Pipeline

```
RAW DATABASE DATA
    │
    ├─ TodayPlan Records: 5 tasks
    │  ├─ Task 1: planned=120 min, status=COMPLETED, quadrant=Q1
    │  ├─ Task 2: planned=120 min, status=IN_ACTIVITY, quadrant=Q1
    │  ├─ Task 3: planned=180 min, status=COMPLETED, quadrant=Q2
    │  ├─ Task 4: planned=90 min, status=COMPLETED, quadrant=Q3
    │  └─ Task 5: planned=90 min, status=PLANNED, quadrant=Q4
    │
    └─ ActivityLog Records: 4 entries
       ├─ Log 1: task=1, worked=70 min, status=STOPPED
       ├─ Log 2: task=1, worked=65 min, status=COMPLETED
       ├─ Log 3: task=2, worked=95 min, status=IN_PROGRESS
       └─ Log 4: task=3, worked=175 min, status=COMPLETED
    │
    ▼
CALCULATION LAYER
    │
    ├─ Sum planned minutes: 120+120+180+90+90 = 600 mins = 10h
    ├─ Sum worked minutes: 70+65+95+175 = 405 mins = 6.75h
    ├─ Extra minutes: 0 (worked less than planned)
    │
    ├─ Completed count: 3 (tasks 1, 3, 4)
    ├─ In Progress: 1 (task 2)
    ├─ Not Started: 1 (task 5)
    │
    ├─ Quadrant totals:
    │  ├─ Q1: 2 tasks, 240 mins planned
    │  ├─ Q2: 1 task, 180 mins planned
    │  ├─ Q3: 1 task, 90 mins planned
    │  └─ Q4: 1 task, 90 mins planned
    │
    └─ Metrics:
       ├─ Completion rate: (3/5) * 100 = 60%
       ├─ Efficiency: (6.75/10) * 100 = 67.5%
       └─ Status: Behind Schedule
    │
    ▼
RESPONSE JSON
    │
    {
      "planned": {
        "total_tasks": 5,
        "total_planned_hours": 10,
        "quadrant_breakdown": {
          "Q1": {"count": 2, "planned_minutes": 240},
          ...
        }
      },
      "actual": {
        "total_hours_worked": 6.75,
        "completed_tasks": 3,
        ...
      },
      "metrics": {
        "task_completion_rate": 60.0,
        "time_efficiency_percentage": 67.5
        ...
      }
    }
```

---

## 🎨 Frontend Component Hierarchy (React Example)

```
PerformanceDashboard (Main Page)
    │
    ├─ DailyPerformanceCard
    │  ├─ StatCard (Planned)
    │  ├─ StatCard (Actual)
    │  ├─ StatCard (Efficiency)
    │  └─ StatusBadge
    │
    ├─ TabsNavigator
    │  ├─ Tab 1: Daily
    │  │  ├─ ProgressBars
    │  │  ├─ PieChart
    │  │  └─ TaskList
    │  │
    │  ├─ Tab 2: Weekly
    │  │  ├─ BarChart (Planned vs Actual)
    │  │  ├─ LineChart (Efficiency Trend)
    │  │  └─ WeeklyMetrics
    │  │
    │  └─ Tab 3: Monthly
    │     ├─ WeeklyTable
    │     ├─ MonthlyMetrics
    │     └─ TrendAnalysis
    │
    ├─ InsightsSection
    │  ├─ KeyInsight 1: "You're on track"
    │  ├─ KeyInsight 2: "Best hour: 10 AM"
    │  └─ KeyInsight 3: "Recommendation: ..."
    │
    └─ DateRangePicker (Optional)
       └─ RangeComparisonView
```

---

## 🔐 Authentication & Security Flow

```
User Login
    │
    ├─→ POST /api/login/
    ├─→ Email + Password
    │
    ▼
Receive Token
    │
    ├─→ HTTP 200 OK
    ├─→ Body: {token: "abc123..."}
    │
    ▼
Store Token
    │
    ├─→ React: localStorage.setItem('token', token)
    ├─→ Flutter: SecureStorage.write(key: 'token', value: token)
    │
    ▼
API Request with Token
    │
    ├─→ GET /api/daily-performance/
    ├─→ Header: Authorization: Bearer abc123...
    │
    ▼
Django Middleware Verification
    │
    ├─→ Extract token from header
    ├─→ Verify token signature
    ├─→ Get user from token
    │
    ▼
User-Specific Query
    │
    ├─→ TodayPlan.objects.filter(user=<verified_user>)
    ├─→ Only return data for authenticated user
    │
    ▼
Return Data
```

---

## 📊 Visualization Rendering Flow

```
API Response Received
    │
    {
      metrics: {
        completion_rate: 60,
        efficiency: 79.41,
        ...
      }
    }
    │
    ▼
Components Extract Data
    │
    ├─→ DailyPerformanceCard extracts top-level metrics
    ├─→ ProgressBar extracts completion data
    ├─→ PieChart extracts task breakdown
    ├─→ BarChart extracts hourly data
    └─→ LineChart extracts daily trend
    │
    ▼
Transform for Chart Library
    │
    ├─→ React-Vis/Recharts expects:
    │  [{date: "2024-04-07", efficiency: 79.41, ...}]
    │
    └─→ FL-Chart (Flutter) expects:
       [FlSpot(x, y), FlSpot(x, y), ...]
    │
    ▼
Render on Screen
    │
    └─→ User sees visual representation
```

---

## 🔄 API Response Size Comparison

```
Small Date (Today)
    │
    ├─→ Tasks: ~5
    └─→ Activity logs: ~10
         │
         ▼
       Response: ~5-10 KB

Weekly Data
    │
    ├─→ Tasks: ~35
    └─→ Activity logs: ~70
         │
         ▼
       Response: ~30-50 KB

Monthly Data
    │
    ├─→ Tasks: ~150
    └─→ Activity logs: ~300
         │
         ▼
       Response: ~100-150 KB ← Consider pagination

Large Date Range (3 months)
    │
    ├─→ Tasks: ~450
    └─→ Activity logs: ~900
         │
         ▼
       Response: ~300+ KB ← Definitely paginate
```

---

## 📱 Mobile vs Desktop Rendering

```
DESKTOP (React)
├─ Sidebar navigation
├─ Full charts (600x300 px)
├─ Data tables
├─ Side-by-side cards
└─ All visualizations visible

MOBILE (Flutter)
├─ Top navigation tabs
├─ Charts adapt (300x250 px)
├─ Scrollable sections
├─ Stacked cards
└─ Tap to expand details

RESPONSIVE BREAKPOINTS
├─ < 600px: Single column (mobile)
├─ 600-1200px: Two columns (tablet)
└─ > 1200px: Three columns (desktop)
```

---

## 🚀 Performance Optimization Strategy

```
Request Optimization
├─ Browser Cache: 5 minutes
├─ HTTP Compression (gzip)
└─ Request only visible date range

Response Optimization
├─ Only include needed fields
├─ Aggregate data before sending
└─ Paginate large responses

Frontend Optimization
├─ Memoize components (React.memo)
├─ Lazy load charts
└─ Virtual scroll for long lists

Database Optimization
├─ Index on (user, plan_date)
├─ Use select_related() for joins
└─ Pre-aggregate daily metrics
```

---

## 📋 Error Handling Flow

```
API Request
    │
    ├─→ Success (200)
    │  └─→ Display data
    │
    ├─→ Bad Request (400)
    │  ├─→ Invalid date format
    │  └─→ Show error message
    │
    ├─→ Unauthorized (401)
    │  ├─→ Token expired
    │  └─→ Redirect to login
    │
    ├─→ Forbidden (403)
    │  ├─→ Access denied
    │  └─→ Show permission error
    │
    ├─→ Not Found (404)
    │  ├─→ User data not found
    │  └─→ Show default state
    │
    └─→ Server Error (500)
       ├─→ Internal error
       └─→ Show retry button
```

---

