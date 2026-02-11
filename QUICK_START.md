# 🚀 Project Work Stats Feature - Quick Start Guide

## ✅ What Was Implemented

The Project Work Stats feature allows you to view project completion percentages based on tasks completed for any team member. This feature is now available for **all user roles** (ADMIN, MANAGER, TEAMLEAD, EMPLOYEE) with appropriate permission controls.

## 📋 Features

- ✓ **User Selection Dropdown** - Select any team member (based on your permissions)
- ✓ **Task-Based Completion Calculation** - Percentages calculated from completed tasks, not hours
- ✓ **Overall Statistics** - See aggregated completion across all projects
- ✓ **Individual Project Breakdown** - View completion percentage for each project
- ✓ **Role-Based Access Control** - Proper permissions for all user types
- ✓ **Real-Time Calculation** - Stats calculated on-the-fly from current data

## 🔑 API Endpoints

### 1. Get Users for Dropdown
```
GET /api/dashboard/users-for-stats/
Authorization: Bearer <access_token>
```

Returns list of users you can view stats for.

### 2. Get Project Work Statistics
```
GET /api/dashboard/project-work-stats/?user_id={user_id}
Authorization: Bearer <access_token>
```

Returns project completion statistics for the specified user.

## 🧪 Testing the Feature

### Option 1: Using Postman

1. **Import the updated collection:**
   - Open Postman
   - Import `PowerPM_API_Tests.postman_collection.json`

2. **Run the requests in order:**
   - Request #1: Login (saves token automatically)
   - Request #5: Get Users for Stats Dropdown
   - Request #6: Get Project Work Stats for Specific User
   - Request #7: Get Project Work Stats for Current User

### Option 2: Using Python Test Script

```bash
# Install requests library
pip install requests

# Run the test script
python test_project_work_stats.py
```

**Note:** Update the credentials in the test file before running.

### Option 3: Using cURL

```bash
# 1. Login first
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"yourpassword"}'

# Copy the access token from response

# 2. Get users
curl -X GET http://localhost:8000/api/dashboard/users-for-stats/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# 3. Get project stats
curl -X GET "http://localhost:8000/api/dashboard/project-work-stats/?user_id=2" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 📊 Example Response

```json
{
    "user": {
        "id": 2,
        "email": "charlie.lead@company.com",
        "name": "Charlie Lead",
        "role": "TEAMLEAD",
        "department": "Engineering"
    },
    "overall_completion_percentage": 44,
    "total_projects": 3,
    "total_tasks": 27,
    "completed_tasks": 12,
    "pending_tasks": 15,
    "projects": [
        {
            "id": 1,
            "name": "Instagram Clone Development",
            "completion_percentage": 40,
            "total_tasks": 10,
            "completed_tasks": 4,
            "pending_tasks": 6
        }
    ]
}
```

## 🔐 Permission Rules

| User Role | Can View Own Stats | Can View Others | Restrictions |
|-----------|-------------------|-----------------|--------------|
| **ADMIN** | ✓ | ✓ All users | None |
| **MANAGER** | ✓ | ✓ Department only | Same department |
| **TEAMLEAD** | ✓ | ✓ Department only | Same department |
| **EMPLOYEE** | ✓ | ✗ | Own stats only |

## 🎯 How It Works

### Calculation Logic

**Per Project:**
```
completion_percentage = (completed_tasks / total_tasks) × 100
```

**Overall:**
```
overall_percentage = (total_completed_tasks_all / total_tasks_all) × 100
```

Where:
- `completed_tasks` = Tasks with status = 'DONE'
- `total_tasks` = All tasks in the project

### Data Source

The feature gets projects from the `Projects` model where:
- `handled_by` field matches the selected user
- Only projects with tasks are included in calculations

## 🖥️ Frontend Integration

### Basic React Example

```jsx
import React, { useState, useEffect } from 'react';

function ProjectWorkStats() {
    const [users, setUsers] = useState([]);
    const [selectedUserId, setSelectedUserId] = useState(null);
    const [stats, setStats] = useState(null);
    const token = localStorage.getItem('access_token');

    // Load users on mount
    useEffect(() => {
        fetch('/api/dashboard/users-for-stats/', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(data => {
            setUsers(data.users);
            if (data.users.length > 0) {
                setSelectedUserId(data.users[0].id);
            }
        });
    }, []);

    // Load stats when user changes
    useEffect(() => {
        if (selectedUserId) {
            fetch(`/api/dashboard/project-work-stats/?user_id=${selectedUserId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
            .then(res => res.json())
            .then(data => setStats(data));
        }
    }, [selectedUserId]);

    return (
        <div className="project-work-stats">
            <h2>Project Work Stats</h2>
            
            {/* User Dropdown */}
            <select 
                value={selectedUserId || ''} 
                onChange={(e) => setSelectedUserId(e.target.value)}
            >
                {users.map(user => (
                    <option key={user.id} value={user.id}>
                        {user.name} ({user.role})
                    </option>
                ))}
            </select>

            {/* Stats Display */}
            {stats && (
                <div className="stats-container">
                    <div className="overall-stats">
                        <h3>Overall Completion: {stats.overall_completion_percentage}%</h3>
                        <p>Total Projects: {stats.total_projects}</p>
                        <p>Total Tasks: {stats.total_tasks}</p>
                        <p>Completed: {stats.completed_tasks}</p>
                    </div>

                    <div className="projects-list">
                        <h3>Projects Breakdown</h3>
                        {stats.projects.map(project => (
                            <div key={project.id} className="project-item">
                                <h4>{project.name}</h4>
                                <div className="progress-bar">
                                    <div 
                                        className="progress-fill" 
                                        style={{width: `${project.completion_percentage}%`}}
                                    >
                                        {project.completion_percentage}%
                                    </div>
                                </div>
                                <p>
                                    {project.completed_tasks}/{project.total_tasks} tasks completed
                                </p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
```

### For Chart.js Integration

```javascript
// After fetching stats
const chartData = {
    labels: stats.projects.map(p => p.name),
    datasets: [{
        label: 'Completion Percentage',
        data: stats.projects.map(p => p.completion_percentage),
        backgroundColor: [
            'rgba(54, 162, 235, 0.8)',
            'rgba(255, 206, 86, 0.8)',
            'rgba(75, 192, 192, 0.8)',
        ]
    }]
};

// Create pie chart
new Chart(ctx, {
    type: 'pie',
    data: chartData
});
```

## 📁 Files Changed

1. **views.py** - Added two new endpoints
   - `users_for_stats()` - Get users for dropdown
   - `project_work_stats()` - Get project statistics (modified)

2. **serializers.py** - Added serializer
   - `ProjectWorkStatsSerializer` - Response structure

3. **PowerPM_API_Tests.postman_collection.json** - Added 3 new requests
   - Get Users for Stats Dropdown
   - Get Project Work Stats for Specific User
   - Get Project Work Stats for Current User

## 📖 Documentation Files

- **PROJECT_WORK_STATS_API.md** - Complete API documentation
- **IMPLEMENTATION_SUMMARY.md** - Technical implementation details
- **test_project_work_stats.py** - Python test script
- **QUICK_START.md** - This file

## ⚙️ Running the Server

```bash
# Navigate to project directory
cd c:\merida\DAS\activity

# Run migrations (if needed)
python manage.py migrate

# Start development server
python manage.py runserver

# Server will be available at http://127.0.0.1:8000
```

## ✨ Quick Verification Checklist

Before testing, make sure you have:

- [ ] At least one user in the database
- [ ] At least one project with `handled_by` field set to a user
- [ ] At least one task associated with that project
- [ ] Some tasks marked as status='DONE' to see non-zero percentages
- [ ] Django server is running
- [ ] Valid authentication token

## 🐛 Troubleshooting

**Issue:** "No projects handled by this user" message
- **Solution:** Create a project and set the `handled_by` field to that user

**Issue:** All percentages showing 0%
- **Solution:** Mark some tasks as status='DONE' in the database

**Issue:** 403 Forbidden error
- **Solution:** Check that you have permission to view that user's stats based on role/department

**Issue:** Token expired error
- **Solution:** Login again to get a fresh access token

## 🎓 Next Steps

1. **Test the API endpoints** using Postman or the Python test script
2. **Integrate with your frontend** using the React example as a guide
3. **Add a pie chart** to visualize project breakdown
4. **Style the interface** to match your dashboard design
5. **Add loading states** and error handling to the frontend

## 📞 Support

For questions or issues:
1. Check the **PROJECT_WORK_STATS_API.md** for detailed API documentation
2. Review the **IMPLEMENTATION_SUMMARY.md** for technical details
3. Run the test script to verify the backend is working correctly

---

**Happy coding! 🎉**
