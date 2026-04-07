# 🚀 Quick Integration Guide for Frontend Developers

## For React Developers (Web)

### Step 1: Create API Service
```jsx
// services/performanceApi.js
import axios from 'axios';

const API_BASE = 'http://your-api.com/api';

export const performanceAPI = {
  // Get today's performance
  getDailyPerformance: (date = null) => {
    const url = date ? `${API_BASE}/daily-performance/${date}/` : `${API_BASE}/daily-performance/`;
    return axios.get(url, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
  },

  // Get performance for date range
  getDateRangePerformance: (startDate, endDate) => {
    return axios.get(`${API_BASE}/daily-performance/range/${startDate}/${endDate}/`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
  },

  // Get this week or specific week
  getWeeklyComparison: (year = null, week = null) => {
    const url = year && week 
      ? `${API_BASE}/weekly-comparison/${year}/${week}/`
      : `${API_BASE}/weekly-comparison/`;
    return axios.get(url, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
  },

  // Get this month or specific month
  getMonthlyComparison: (year = null, month = null) => {
    const url = year && month
      ? `${API_BASE}/monthly-comparison/${year}/${month}/`
      : `${API_BASE}/monthly-comparison/`;
    return axios.get(url, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
  },

  // Get comprehensive dashboard
  getPerformanceDashboard: () => {
    return axios.get(`${API_BASE}/performance-dashboard/`, {
      headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
    });
  }
};
```

### Step 2: Create Hooks
```jsx
// hooks/usePerformance.js
import { useState, useEffect } from 'react';
import { performanceAPI } from '../services/performanceApi';

export const useDailyPerformance = (date = null) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    performanceAPI.getDailyPerformance(date)
      .then(res => setData(res.data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [date]);

  return { data, loading, error };
};

export const usePerformanceDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    performanceAPI.getPerformanceDashboard()
      .then(res => setData(res.data))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
};
```

### Step 3: Create Components
```jsx
// components/PerformanceDashboard.jsx
import React from 'react';
import { usePerformanceDashboard } from '../hooks/usePerformance';
import DailyCard from './DailyCard';
import WeeklyCard from './WeeklyCard';
import MonthlyCard from './MonthlyCard';

const PerformanceDashboard = () => {
  const { data, loading, error } = usePerformanceDashboard();

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!data) return <div>No data</div>;

  return (
    <div className="dashboard">
      <h1>Performance Dashboard</h1>
      <div className="grid">
        <DailyCard data={data.today} />
        <WeeklyCard data={data.this_week} />
        <MonthlyCard data={data.this_month} />
      </div>
      <InsightsSection insights={data.key_insights} />
    </div>
  );
};

export default PerformanceDashboard;
```

---

## For Flutter Developers (Mobile)

### Step 1: Create API Service
```dart
// lib/services/performance_api_service.dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:secure_storage/secure_storage.dart';

class PerformanceAPIService {
  static const String baseUrl = 'https://your-api.com/api';
  final _storage = SecureStorage();

  Future<Map<String, dynamic>> getDailyPerformance({String? date}) async {
    final token = await _storage.read(key: 'auth_token');
    final url = date != null 
      ? '$baseUrl/daily-performance/$date/'
      : '$baseUrl/daily-performance/';
    
    final response = await http.get(
      Uri.parse(url),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load performance data');
    }
  }

  Future<Map<String, dynamic>> getPerformanceDashboard() async {
    final token = await _storage.read(key: 'auth_token');
    
    final response = await http.get(
      Uri.parse('$baseUrl/performance-dashboard/'),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load dashboard');
    }
  }

  Future<Map<String, dynamic>> getWeeklyComparison({int? year, int? week}) async {
    final token = await _storage.read(key: 'auth_token');
    final url = year != null && week != null
      ? '$baseUrl/weekly-comparison/$year/$week/'
      : '$baseUrl/weekly-comparison/';
    
    final response = await http.get(
      Uri.parse(url),
      headers: {'Authorization': 'Bearer $token'},
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load weekly data');
    }
  }
}
```

### Step 2: Create Provider
```dart
// lib/providers/performance_provider.dart
import 'package:flutter/material.dart';
import '../services/performance_api_service.dart';

class PerformanceProvider with ChangeNotifier {
  final _service = PerformanceAPIService();
  
  Map<String, dynamic>? _dailyData;
  Map<String, dynamic>? _weeklyData;
  bool _loading = false;
  String? _error;

  // Getters
  Map<String, dynamic>? get dailyData => _dailyData;
  Map<String, dynamic>? get weeklyData => _weeklyData;
  bool get loading => _loading;
  String? get error => _error;

  // Methods
  Future<void> fetchDailyPerformance({String? date}) async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      _dailyData = await _service.getDailyPerformance(date: date);
    } catch (e) {
      _error = e.toString();
    }

    _loading = false;
    notifyListeners();
  }

  Future<void> fetchWeeklyComparison({int? year, int? week}) async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      _weeklyData = await _service.getWeeklyComparison(year: year, week: week);
    } catch (e) {
      _error = e.toString();
    }

    _loading = false;
    notifyListeners();
  }
}
```

### Step 3: Create Widget
```dart
// lib/screens/performance_dashboard.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import '../providers/performance_provider.dart';

class PerformanceDashboard extends StatefulWidget {
  @override
  _PerformanceDashboardState createState() => _PerformanceDashboardState();
}

class _PerformanceDashboardState extends State<PerformanceDashboard> {
  @override
  void initState() {
    super.initState();
    // Fetch data when screen loads
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<PerformanceProvider>().fetchDailyPerformance();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Performance Dashboard')),
      body: Consumer<PerformanceProvider>(
        builder: (context, provider, _) {
          if (provider.loading) {
            return Center(child: CircularProgressIndicator());
          }
          
          if (provider.error != null) {
            return Center(child: Text('Error: ${provider.error}'));
          }

          final data = provider.dailyData;
          if (data == null) return SizedBox.shrink();

          return SingleChildScrollView(
            child: Column(
              children: [
                _buildDailyCard(data),
                _buildProgressBars(data),
                _buildPieChart(data),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildDailyCard(Map<String, dynamic> data) {
    final planned = data['planned'];
    final actual = data['actual'];
    final metrics = data['metrics'];

    return Card(
      margin: EdgeInsets.all(16),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Today\'s Performance', style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _statColumn('Planned', '${planned['total_planned_hours']}h', Colors.blue),
                _statColumn('Actual', '${actual['total_hours_worked']}h', Colors.green),
                _statColumn('Efficiency', '${metrics['time_efficiency_percentage']}%', 
                  metrics['time_efficiency_percentage'] >= 80 ? Colors.green : Colors.orange),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildProgressBars(Map<String, dynamic> data) {
    final planned = data['planned'];
    final actual = data['actual'];

    return Card(
      margin: EdgeInsets.all(16),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Task Progress', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            _progressBar(
              actual['completed_tasks'],
              planned['total_tasks'],
              'Tasks'
            ),
            SizedBox(height: 16),
            Text('Hours Progress', style: TextStyle(fontWeight: FontWeight.bold)),
            SizedBox(height: 8),
            _progressBar(
              actual['total_hours_worked'],
              planned['total_planned_hours'],
              'Hours'
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPieChart(Map<String, dynamic> data) {
    final metrics = data['metrics'];
    final breakdown = metrics['task_breakdown'];

    return Card(
      margin: EdgeInsets.all(16),
      child: Padding(
        padding: EdgeInsets.all(16),
        child: SizedBox(
          height: 300,
          child: PieChart(
            PieChartData(
              sections: [
                PieChartSectionData(
                  value: breakdown['completed'].toDouble(),
                  title: 'Completed',
                  color: Colors.green,
                ),
                PieChartSectionData(
                  value: breakdown['in_progress'].toDouble(),
                  title: 'In Progress',
                  color: Colors.amber,
                ),
                PieChartSectionData(
                  value: breakdown['not_started'].toDouble(),
                  title: 'Not Started',
                  color: Colors.red,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _statColumn(String label, String value, Color color) {
    return Column(
      children: [
        Text(label, style: TextStyle(fontSize: 12, color: Colors.grey)),
        SizedBox(height: 4),
        Text(value, style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: color)),
      ],
    );
  }

  Widget _progressBar(dynamic completed, dynamic total, String label) {
    final percentage = (completed / total);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LinearProgressIndicator(
          value: percentage,
          minHeight: 8,
          backgroundColor: Colors.grey[300],
          valueColor: AlwaysStoppedAnimation(
            percentage >= 0.8 ? Colors.green : percentage >= 0.5 ? Colors.orange : Colors.red
          ),
        ),
        SizedBox(height: 4),
        Text('$completed/$total $label - ${(percentage * 100).toStringAsFixed(1)}%', 
          style: TextStyle(fontSize: 12)),
      ],
    );
  }
}
```

---

## Integration Checklist

### Backend
- ✅ APIs deployed and tested
- ✅ Endpoints return correct data
- ✅ Authentication working

### Frontend (React)
- [ ] Install dependencies: `npm install axios recharts`
- [ ] Create `services/performanceApi.js`
- [ ] Create `hooks/usePerformance.js`
- [ ] Create components for dashboard
- [ ] Test with API

### Frontend (Flutter)
- [ ] Add dependencies: `http`, `fl_chart`, `provider`
- [ ] Create `PerformanceAPIService`
- [ ] Create `PerformanceProvider`
- [ ] Create dashboard screen
- [ ] Test with API

---

## Testing Endpoints

```bash
# Test in Postman or cURL
curl -X GET http://localhost:8000/api/daily-performance/ \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

