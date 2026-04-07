# Implementation Examples & Frontend Code Snippets

## Quick Start Guide

### **Backend Setup (Python/Django)**

#### 1. Already done in Django
✅ Models: `TodayPlan`, `ActivityLog`, `DailyPlanner`
✅ Serializers in `serializers_performance.py`
✅ Views in `views_performance.py`
✅ URLs in `urls.py`

#### 2. Run migrations (if needed)
```bash
cd DAS_Backend
python manage.py makemigrations
python manage.py migrate
```

#### 3. Start development server
```bash
python manage.py runserver
```

---

## Frontend Implementation Examples

### **React.js - Daily Performance Card**

```jsx
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, PieChart, Pie, Cell } from 'recharts';

const DailyPerformanceCard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDailyPerformance();
  }, []);

  const fetchDailyPerformance = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/api/daily-performance/', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      setData(response.data);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  const { planned, actual, metrics, tasks } = data;
  
  // Color based on efficiency
  const getStatusColor = (efficiency) => {
    if (efficiency >= 80) return '#4CAF50'; // Green
    if (efficiency >= 50) return '#FF9800'; // Orange
    return '#F44336'; // Red
  };

  return (
    <div className="performance-card">
      <h2>Today's Performance</h2>
      
      {/* Top Stats */}
      <div className="stats-row">
        <div className="stat">
          <span className="label">Planned</span>
          <span className="value">{planned.total_planned_hours}h</span>
          <span className="sublabel">{planned.total_tasks} tasks</span>
        </div>
        
        <div className="stat">
          <span className="label">Actual</span>
          <span className="value">{actual.total_hours_worked}h</span>
          <span className="sublabel">{actual.completed_tasks} completed</span>
        </div>
        
        <div className="stat">
          <span className="label">Efficiency</span>
          <span className="value" style={{ color: getStatusColor(metrics.time_efficiency_percentage) }}>
            {metrics.time_efficiency_percentage}%
          </span>
          <span className="sublabel">{metrics.status}</span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="progress-section">
        <h4>Task Progress</h4>
        <ProgressBar 
          completed={actual.completed_tasks} 
          total={planned.total_tasks}
          label="Tasks"
        />
        <h4>Hours Progress</h4>
        <ProgressBar 
          completed={actual.total_hours_worked} 
          total={planned.total_planned_hours}
          label="Hours"
        />
      </div>

      {/* Pie Chart */}
      <PieChart width={300} height={300}>
        <Pie
          data={[
            { name: 'Completed', value: metrics.task_breakdown.completed },
            { name: 'In Progress', value: metrics.task_breakdown.in_progress },
            { name: 'Not Started', value: metrics.task_breakdown.not_started }
          ]}
          cx={150}
          cy={150}
          outerRadius={100}
          label
        >
          <Cell fill="#4CAF50" /> {/* Green for completed */}
          <Cell fill="#FFC107" /> {/* Yellow for in progress */}
          <Cell fill="#F44336" /> {/* Red for not started */}
        </Pie>
      </PieChart>
    </div>
  );
};

// Helper Component: Progress Bar
const ProgressBar = ({ completed, total, label }) => {
  const percentage = (completed / total) * 100;
  
  return (
    <div className="progress-bar-container">
      <div className="progress-bar">
        <div 
          className="progress-fill" 
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="progress-label">{completed}/{total} {label} - {percentage.toFixed(1)}%</span>
    </div>
  );
};

export default DailyPerformanceCard;
```

---

### **React.js - Weekly Comparison Chart**

```jsx
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

const WeeklyComparison = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWeeklyData();
  }, []);

  const fetchWeeklyData = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/api/weekly-comparison/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setData(response.data);
      setLoading(false);
    } catch (err) {
      console.error('Error:', err);
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (!data) return <div>No data</div>;

  return (
    <div className="weekly-comparison">
      <h2>Weekly Performance</h2>
      
      {/* Bar Chart: Planned vs Actual */}
      <BarChart width={600} height={300} data={data.daily_breakdown}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey="planned_hours" fill="#8884d8" name="Planned Hours" />
        <Bar dataKey="actual_hours" fill="#82ca9d" name="Actual Hours" />
      </BarChart>

      {/* Line Chart: Efficiency Trend */}
      <LineChart width={600} height={300} data={data.daily_breakdown}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="date" />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line 
          type="monotone" 
          dataKey="efficiency" 
          stroke="#ffc658" 
          name="Efficiency %" 
        />
        <Line 
          type="monotone" 
          dataKey="completion_rate" 
          stroke="#ff7c7c" 
          name="Completion %"
        />
      </LineChart>

      {/* Summary Cards */}
      <div className="summary-cards">
        <Card>
          <h4>Total Planned</h4>
          <p className="large">{data.weekly_totals.total_planned_hours}h</p>
        </Card>
        <Card>
          <h4>Total Worked</h4>
          <p className="large">{data.weekly_totals.total_actual_hours}h</p>
        </Card>
        <Card>
          <h4>Completion Rate</h4>
          <p className="large">{data.weekly_totals.weekly_completion_rate.toFixed(1)}%</p>
        </Card>
        <Card>
          <h4>Efficiency</h4>
          <p className="large">{data.weekly_metrics.weekly_efficiency.toFixed(1)}%</p>
        </Card>
      </div>
    </div>
  );
};

const Card = ({ children }) => (
  <div className="summary-card">
    {children}
  </div>
);

export default WeeklyComparison;
```

---

### **Flutter - Daily Performance Widget**

```dart
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:fl_chart/fl_chart.dart';

class DailyPerformanceWidget extends StatefulWidget {
  @override
  _DailyPerformanceState createState() => _DailyPerformanceState();
}

class _DailyPerformanceState extends State<DailyPerformanceWidget> {
  late Future<Map<String, dynamic>> performanceData;
  
  @override
  void initState() {
    super.initState();
    performanceData = fetchDailyPerformance();
  }

  Future<Map<String, dynamic>> fetchDailyPerformance() async {
    final token = ''; // Get from secure storage
    final response = await http.get(
      Uri.parse('https://api.example.com/api/daily-performance/'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load performance data');
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: performanceData,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return CircularProgressIndicator();
        }
        
        if (snapshot.hasError) {
          return Text('Error: ${snapshot.error}');
        }

        final data = snapshot.data!;
        final planned = data['planned'];
        final actual = data['actual'];
        final metrics = data['metrics'];

        return SingleChildScrollView(
          child: Column(
            children: [
              // Top Stats Card
              Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    children: [
                      Text('Today\'s Performance', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                      SizedBox(height: 16),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceAround,
                        children: [
                          _buildStatColumn('Planned', '${planned['total_planned_hours']}h', Colors.blue),
                          _buildStatColumn('Actual', '${actual['total_hours_worked']}h', Colors.green),
                          _buildStatColumn('Efficiency', '${metrics['time_efficiency_percentage']}%', 
                            metrics['time_efficiency_percentage'] >= 80 ? Colors.green : Colors.orange),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              SizedBox(height: 16),
              
              // Progress Bars
              Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Task Progress', style: TextStyle(fontWeight: FontWeight.bold)),
                      SizedBox(height: 8),
                      _buildProgressBar(
                        actual['completed_tasks'],
                        planned['total_tasks'],
                        'Tasks'
                      ),
                      SizedBox(height: 16),
                      Text('Hours Progress', style: TextStyle(fontWeight: FontWeight.bold)),
                      SizedBox(height: 8),
                      _buildProgressBar(
                        actual['total_hours_worked'],
                        planned['total_planned_hours'],
                        'Hours'
                      ),
                    ],
                  ),
                ),
              ),
              SizedBox(height: 16),
              
              // Pie Chart
              Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: SizedBox(
                    height: 300,
                    child: PieChart(
                      PieChartData(
                        sections: [
                          PieChartSectionData(
                            value: metrics['task_breakdown']['completed'].toDouble(),
                            title: 'Completed\n${metrics['task_breakdown']['completed']}',
                            color: Colors.green,
                            radius: 100,
                          ),
                          PieChartSectionData(
                            value: metrics['task_breakdown']['in_progress'].toDouble(),
                            title: 'In Progress\n${metrics['task_breakdown']['in_progress']}',
                            color: Colors.amber,
                            radius: 100,
                          ),
                          PieChartSectionData(
                            value: metrics['task_breakdown']['not_started'].toDouble(),
                            title: 'Not Started\n${metrics['task_breakdown']['not_started']}',
                            color: Colors.red,
                            radius: 100,
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildStatColumn(String label, String value, Color color) {
    return Column(
      children: [
        Text(label, style: TextStyle(fontSize: 12, color: Colors.grey)),
        SizedBox(height: 4),
        Text(value, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: color)),
      ],
    );
  }

  Widget _buildProgressBar(dynamic completed, dynamic total, String label) {
    final percentage = (completed / total) * 100;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LinearProgressIndicator(
          value: completed / total,
          minHeight: 8,
          backgroundColor: Colors.grey[300],
          valueColor: AlwaysStoppedAnimation(
            percentage >= 80 ? Colors.green : percentage >= 50 ? Colors.orange : Colors.red
          ),
        ),
        SizedBox(height: 4),
        Text('$completed/$total $label - ${percentage.toStringAsFixed(1)}%', style: TextStyle(fontSize: 12)),
      ],
    );
  }
}
```

---

### **Testing with cURL**

```bash
# Get today's performance
curl -X GET http://localhost:8000/api/daily-performance/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get specific date
curl -X GET http://localhost:8000/api/daily-performance/2024-04-07/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get weekly data
curl -X GET http://localhost:8000/api/weekly-comparison/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get monthly data
curl -X GET "http://localhost:8000/api/monthly-comparison/2024/4/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get date range
curl -X GET "http://localhost:8000/api/daily-performance/range/2024-04-01/2024-04-07/" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get dashboard
curl -X GET http://localhost:8000/api/performance-dashboard/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### **Postman Collection**

```json
{
  "info": {
    "name": "Performance API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Daily Performance",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{token}}"
          }
        ],
        "url": {
          "raw": "{{base_url}}/api/daily-performance/",
          "path": ["api", "daily-performance"]
        }
      }
    },
    {
      "name": "Weekly Comparison",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{token}}"
          }
        ],
        "url": {
          "raw": "{{base_url}}/api/weekly-comparison/",
          "path": ["api", "weekly-comparison"]
        }
      }
    }
  ]
}
```

---

## Environment Variables

Create `.env` file in DAS_Backend:

```
# API Configuration
API_BASE_URL=http://localhost:8000/api
API_TIMEOUT=30

# Database
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3

# Frontend URLs
FRONTEND_URL=http://localhost:3000
MOBILE_APP_URL=app://das

# Cache (for performance optimization)
CACHE_ENABLED=True
CACHE_TIMEOUT=300
```

---

## Performance Tips

1. **Pagination** - For large date ranges, add pagination
2. **Caching** - Cache results for 5 minutes
3. **Indexes** - Add database indexes on `user` and `plan_date` fields
4. **Lazy Loading** - Load detailed tasks only when needed
5. **Background Jobs** - Pre-calculate metrics with Celery

---

