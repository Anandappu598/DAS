# API Quick Reference Guide

## 🚀 Getting Started - Copy & Paste Examples

### 1. Get Today's Performance Data

#### RequestURL
```
GET http://localhost:8000/api/daily-performance/
```

#### JavaScript/Fetch
```javascript
fetch('http://localhost:8000/api/daily-performance/', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  }
})
.then(res => res.json())
.then(data => {
  console.log('Daily Plan Target:', data.planned_summary.daily_plan.planned_hours);
  console.log('Planned Tasks:', data.planned_summary.planned_tasks.count);
  console.log('Unplanned Tasks:', data.planned_summary.unplanned_tasks.count);
  console.log('Hours Worked Today:', data.actual_summary.total_hours_worked);
})
```

#### Python
```python
import requests

response = requests.get(
    'http://localhost:8000/api/daily-performance/',
    headers={'Authorization': 'Bearer YOUR_TOKEN'}
)

data = response.json()
daily_plan = data['planned_summary']['daily_plan']
print(f"Daily Target: {daily_plan['planned_hours']}h")
print(f"Planned Tasks: {data['planned_summary']['planned_tasks']['count']}")
print(f"Hours Worked: {data['actual_summary']['total_hours_worked']}h")
```

#### cURL
```bash
curl -X GET 'http://localhost:8000/api/daily-performance/' \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

---

### 2. Get Specific Date Data

#### Request
```
GET http://localhost:8000/api/daily-performance/2026-04-07/
```

#### Response (Shortened)
```json
{
  "date": "2026-04-07",
  "user": "user@example.com",
  "planned_summary": {
    "daily_plan": {
      "date": "2026-04-07",
      "planned_hours": 8.0,
      "has_daily_planner": true
    },
    "total_tasks": 5,
    "planned_tasks": {
      "count": 4,
      "total_hours": 7.5,
      "tasks": [
        {
          "id": 1,
          "name": "API Development",
          "planned_hours": 2.0,
          "status": "COMPLETED",
          "quadrant": "Q1"
        }
      ]
    },
    "unplanned_tasks": {
      "count": 1,
      "total_hours": 1.0,
      "tasks": [
        {
          "id": 5,
          "name": "Bug Fix",
          "planned_hours": 1.0,
          "status": "COMPLETED",
          "quadrant": "Q3"
        }
      ]
    }
  },
  "actual_summary": {
    "total_hours_worked": 6.75,
    "planned_work": {
      "count": 4,
      "total_hours": 5.92,
      "tasks": [
        {
          "id": 1,
          "name": "API Development",
          "planned_hours": 2.0,
          "actual_hours": 2.25,
          "completed": true
        }
      ]
    },
    "unplanned_work": {
      "count": 1,
      "total_hours": 0.83
    }
  },
  "metrics": {
    "task_completion_rate": 60.0,
    "time_efficiency_percentage": 79.41
  }
}
```

---

### 3. Date Range Query

#### Request
```
GET http://localhost:8000/api/daily-performance/range/2026-04-01/2026-04-07/
```

#### JavaScript
```javascript
const startDate = '2026-04-01';
const endDate = '2026-04-07';

fetch(`/api/daily-performance/range/${startDate}/${endDate}/`, {
  headers: {'Authorization': 'Bearer YOUR_TOKEN'}
})
.then(res => res.json())
.then(data => {
  // Returns array of daily performance data
  data.forEach(day => {
    console.log(`${day.date}: ${day.actual_summary.total_hours_worked}h worked`);
  });
})
```

---

### 4. Weekly Comparison

#### Request
```
GET http://localhost:8000/api/weekly-comparison/
GET http://localhost:8000/api/weekly-comparison/2026-04-07/
```

#### Response Structure
```json
{
  "week_starting": "2026-04-07",
  "week_ending": "2026-04-13",
  "user": "user@example.com",
  "daily_data": [
    {
      "date": "2026-04-07",
      "planned_hours": 8.0,
      "actual_hours": 6.75,
      "task_completion_rate": 60.0,
      "efficiency": 79.41
    },
    // ... 7 days total
  ],
  "weekly_summary": {
    "total_planned_hours": 56.0,
    "total_actual_hours": 47.5,
    "average_daily_efficiency": 84.82,
    "most_productive_day": "2026-04-09",
    "least_productive_day": "2026-04-06"
  }
}
```

#### React Component Template
```jsx
function WeeklyView() {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    fetch('/api/weekly-comparison/')
      .then(res => res.json())
      .then(data => setData(data));
  }, []);
  
  if (!data) return <div>Loading...</div>;
  
  return (
    <div>
      <h2>Week of {data.week_starting}</h2>
      <p>Total Planned: {data.weekly_summary.total_planned_hours}h</p>
      <p>Total Actual: {data.weekly_summary.total_actual_hours}h</p>
      <p>Efficiency: {data.weekly_summary.average_daily_efficiency.toFixed(1)}%</p>
      
      <table>
        <tr><th>Date</th><th>Target</th><th>Actual</th><th>Efficiency</th></tr>
        {data.daily_data.map(day => (
          <tr key={day.date}>
            <td>{day.date}</td>
            <td>{day.planned_hours}h</td>
            <td>{day.actual_hours}h</td>
            <td>{day.efficiency.toFixed(1)}%</td>
          </tr>
        ))}
      </table>
    </div>
  );
}
```

---

### 5. Monthly Comparison

#### Request
```
GET http://localhost:8000/api/monthly-comparison/
GET http://localhost:8000/api/monthly-comparison/2026-04/
```

#### Key Metrics
```json
{
  "month": "2026-04",
  "user": "user@example.com",
  "monthly_summary": {
    "total_planned_hours": 160.0,
    "total_actual_hours": 145.0,
    "average_daily_target": 8.0,
    "average_daily_actual": 7.3,
    "task_completion_rate": 78.5,
    "most_productive_week": "Week of 2026-04-07",
    "days_on_track": 20,
    "days_behind": 10
  }
}
```

---

### 6. Dashboard Overview

#### Request
```
GET http://localhost:8000/api/performance-dashboard/
```

#### Response
```json
{
  "user": "user@example.com",
  "today": {
    "date": "2026-04-07",
    "daily_plan_target": 8.0,
    "tasks_planned": 4,
    "tasks_unplanned": 1,
    "hours_worked": 6.75,
    "completion_rate": 60.0
  },
  "this_week": {
    "total_planned": 56.0,
    "total_actual": 47.5,
    "average_efficiency": 84.82
  },
  "this_month": {
    "total_planned": 160.0,
    "total_actual": 145.0,
    "days_on_track": 20,
    "days_behind": 10
  },
  "trends": {
    "best_performing_day": "Wednesday",
    "most_worked_quadrant": "Q1"
  }
}
```

#### Single Dashboard Component
```jsx
function Dashboard() {
  const [data, setData] = useState(null);
  
  useEffect(() => {
    fetch('/api/performance-dashboard/')
      .then(res => res.json())
      .then(data => setData(data));
  }, []);
  
  if (!data) return <div>Loading...</div>;
  
  const { today, this_week, this_month } = data;
  
  return (
    <div className="dashboard">
      <h1>Performance Dashboard</h1>
      
      {/* Today Card */}
      <Card title="Today">
        <Stat label="Target" value={`${today.daily_plan_target}h`} />
        <Stat label="Worked" value={`${today.hours_worked}h`} />
        <Stat label="Progress" value={`${today.completion_rate}%`} />
      </Card>
      
      {/* Week Card */}
      <Card title="This Week">
        <Stat label="Planned" value={`${this_week.total_planned}h`} />
        <Stat label="Actual" value={`${this_week.total_actual}h`} />
        <Stat label="Efficiency" value={`${this_week.average_efficiency.toFixed(1)}%`} />
      </Card>
      
      {/* Month Card */}
      <Card title="This Month">
        <Stat label="Planned" value={`${this_month.total_planned}h`} />
        <Stat label="Actual" value={`${this_month.total_actual}h`} />
        <Stat label="On Track" value={`${this_month.days_on_track}/30 days`} />
      </Card>
    </div>
  );
}
```

---

## Common Patterns

### 1. Check if Day is On Track

```javascript
function isDayOnTrack(dailyData) {
  const { planned_summary, actual_summary, metrics } = dailyData;
  const targetHours = planned_summary.daily_plan.planned_hours || planned_summary.total_planned_hours;
  const workedHours = actual_summary.total_hours_worked;
  
  // On track if worked >= 80% of target
  return (workedHours / targetHours) >= 0.8;
}
```

### 2. Show Task Progress

```javascript
function renderTaskProgress(task, actual) {
  const plannedMinutes = task.planned_minutes;
  const actualMinutes = actual.actual_minutes || 0;
  const completed = actual.completed ? '✓' : '⏳';
  
  return `${completed} ${task.name}: ${idealMinutes}m planned, ${actualMinutes}m done`;
}
```

### 3. Calculate Efficiency

```javascript
function calculateEfficiency(planned, actual) {
  // How efficiently time was used
  return (actual / planned) * 100; // >= 100% means did more than planned
}

// Usage:
const efficiency = calculateEfficiency(
  data.planned_summary.total_planned_hours,
  data.actual_summary.total_hours_worked
);
```

### 4. Get Unplanned Work Percentage

```javascript
function getUnplannedPercentage(data) {
  const total = data.actual_summary.total_hours_worked;
  const unplanned = data.actual_summary.unplanned_work.total_hours;
  return total > 0 ? (unplanned / total) * 100 : 0;
}
```

### 5. Find Most Productive Task

```javascript
function getMostProductiveTask(data) {
  const allTasks = [
    ...data.actual_summary.planned_work.tasks,
    ...data.actual_summary.unplanned_work.tasks
  ];
  
  return allTasks.reduce((max, task) => 
    task.actual_hours > (max.actual_hours || 0) ? task : max
  );
}
```

---

## Error Handling

### Complete Example with Error Handling

```javascript
async function fetchDailyPerformance(date = null) {
  try {
    const endpoint = date 
      ? `/api/daily-performance/${date}/`
      : '/api/daily-performance/';
    
    const response = await fetch(endpoint, {
      headers: {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Unauthorized - Please login again');
      } else if (response.status === 404) {
        throw new Error('No data found for this date');
      } else {
        throw new Error(`API Error: ${response.status}`);
      }
    }
    
    const data = await response.json();
    return data;
    
  } catch (error) {
    console.error('Error fetching performance data:', error);
    // Show user-friendly error message
    return null;
  }
}
```

---

## Response Field Reference

### Daily Plan Section
```
planned_summary.daily_plan
├─ date: string (YYYY-MM-DD)
├─ planned_hours: float (e.g., 8.0) or null
└─ has_daily_planner: boolean
```

### Planned Tasks
```
planned_summary.planned_tasks
├─ count: integer
├─ total_hours: float
├─ total_minutes: integer
└─ tasks: array
   ├─ id: integer
   ├─ name: string
   ├─ planned_hours: float
   ├─ planned_minutes: integer
   ├─ status: string (PLANNED, IN_ACTIVITY, COMPLETED)
   ├─ quadrant: string (Q1, Q2, Q3, Q4)
   └─ notes: string or null
```

### Reported Work
```
actual_summary.planned_work
├─ count: integer
├─ total_hours: float
├─ total_minutes: integer
└─ tasks: array
   ├─ id: integer
   ├─ name: string
   ├─ planned_hours: float
   ├─ actual_hours: float
   ├─ actual_minutes: integer
   ├─ status: string
   ├─ completed: boolean
   └─ activity_sessions: integer
```

### Metrics
```
metrics
├─ task_completion_rate: float (0-100)
├─ time_efficiency_percentage: float (0-100+)
├─ hour_difference: float (actual - planned)
├─ minute_difference: integer (actual - planned)
├─ planned_vs_actual
│  ├─ planned: float
│  ├─ actual: float
│  └─ difference: float
└─ status: string (On Track, Behind, Ahead)
```

---

## Troubleshooting

### Issue: No data returned
```javascript
// Check if user has DailyPlan entries
// Check if user has ActivityLog entries
// Verify date format is YYYY-MM-DD
```

### Issue: daily_plan is null
```javascript
// This is normal - means no DailyPlanner entry for that day
// Check has_daily_planner flag: if false, no plan was set
if (data.planned_summary.daily_plan.has_daily_planner) {
  // Use the planned_hours
} else {
  // Use total_planned_hours from tasks as fallback
  const fallback = data.planned_summary.total_planned_hours;
}
```

### Issue: Wrong date format
```javascript
// ❌ Wrong: getDate('04-07-2026')
// ✅ Correct: getDate('2026-04-07')

// Utility to format dates
function formatDate(date) {
  return date.toISOString().split('T')[0];
}
```

---

## Performance Tips

1. **Cache responses** - Don't refetch same date multiple times
2. **Use date range** - More efficient than individual requests
3. **Paginate if needed** - Don't load all months at once
4. **Use dashboard endpoint** - Pre-calculated summary data

---

## Next: Frontend Implementation

Ready to build the dashboard? See:
- `API_DAILY_PLAN_INCLUDED.md` - Full response examples
- `FRONTEND_IMPLEMENTATION_EXAMPLES.md` - React/Flutter code
- `DASHBOARD_VISUALIZATION_GUIDE.md` - Chart suggestions

