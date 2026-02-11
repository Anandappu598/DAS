# Project Work Stats API Documentation

This document describes the API endpoints for the Project Work Stats feature, which allows users to view project completion statistics based on tasks completed.

## Overview

The Project Work Stats feature calculates project completion percentages based on the number of tasks completed vs total tasks for projects handled by a specific user. This feature is available to all user roles with appropriate permission controls.

## API Endpoints

### 1. Get Users for Stats Dropdown

**Endpoint:** `GET /api/dashboard/users-for-stats/`

**Description:** Returns a list of users that can be selected in the project work stats dropdown, based on the current user's role and permissions.

**Permission Rules:**
- **ADMIN**: Can see all active users
- **MANAGER/TEAMLEAD**: Can see users from their department only
- **EMPLOYEE**: Can only see themselves

**Request:**
```http
GET /api/dashboard/users-for-stats/
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "count": 5,
    "users": [
        {
            "id": 1,
            "email": "john.doe@company.com",
            "name": "John Doe",
            "role": "EMPLOYEE",
            "role_display": "Employee",
            "department": "Engineering",
            "projects_count": 3
        },
        {
            "id": 2,
            "email": "charlie.lead@company.com",
            "name": "Charlie Lead",
            "role": "TEAMLEAD",
            "role_display": "Team Lead",
            "department": "Engineering",
            "projects_count": 5
        }
    ]
}
```

### 2. Get Project Work Statistics

**Endpoint:** `GET /api/dashboard/project-work-stats/?user_id={user_id}`

**Description:** Returns project work statistics for a specific user, showing completion percentages based on tasks completed for each project handled by that user.

**Query Parameters:**
- `user_id` (optional): The ID of the user to get statistics for. Defaults to the current logged-in user.

**Permission Rules:**
- Users can always view their own statistics
- **ADMIN**: Can view statistics for any user
- **MANAGER/TEAMLEAD**: Can view statistics for users in their department
- **EMPLOYEE**: Can only view their own statistics

**Request:**
```http
GET /api/dashboard/project-work-stats/?user_id=2
Authorization: Bearer <access_token>
```

**Response:**
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
            "status": "ACTIVE",
            "total_tasks": 10,
            "completed_tasks": 4,
            "pending_tasks": 6,
            "completion_percentage": 40,
            "start_date": "2026-01-15",
            "due_date": "2026-03-15",
            "working_hours": 216
        },
        {
            "id": 2,
            "name": "Legacy Knowledge Base Migration",
            "status": "ACTIVE",
            "total_tasks": 9,
            "completed_tasks": 3,
            "pending_tasks": 6,
            "completion_percentage": 33,
            "start_date": "2026-01-20",
            "due_date": "2026-02-28",
            "working_hours": 160
        },
        {
            "id": 3,
            "name": "E-commerce Platform",
            "status": "ACTIVE",
            "total_tasks": 8,
            "completed_tasks": 5,
            "pending_tasks": 3,
            "completion_percentage": 63,
            "start_date": "2026-02-01",
            "due_date": "2026-04-01",
            "working_hours": 112
        }
    ]
}
```

**Response (No Projects):**
```json
{
    "user": {
        "id": 5,
        "email": "new.employee@company.com",
        "name": "New Employee",
        "role": "EMPLOYEE",
        "department": "Engineering"
    },
    "total_percentage": 100,
    "message": "No projects handled by this user.",
    "projects": []
}
```

**Error Responses:**

1. User not found:
```json
{
    "error": "User not found"
}
```
Status: 404 NOT FOUND

2. Permission denied:
```json
{
    "error": "You can only view members from your department"
}
```
Status: 403 FORBIDDEN

3. Employee trying to view others:
```json
{
    "error": "You do not have permission to view other users statistics"
}
```
Status: 403 FORBIDDEN

## Usage Examples

### Example 1: Admin Getting Stats for a Team Lead

```javascript
// Admin user wants to see stats for Charlie Lead (user_id: 2)
const response = await fetch('/api/dashboard/project-work-stats/?user_id=2', {
    headers: {
        'Authorization': `Bearer ${accessToken}`
    }
});

const data = await response.json();
console.log(`${data.user.name} has completed ${data.overall_completion_percentage}% of their projects`);
```

### Example 2: Employee Viewing Their Own Stats

```javascript
// Employee viewing their own stats (no user_id parameter)
const response = await fetch('/api/dashboard/project-work-stats/', {
    headers: {
        'Authorization': `Bearer ${accessToken}`
    }
});

const data = await response.json();
// Will show stats for the current logged-in user
```

### Example 3: Manager Viewing Team Member Stats

```javascript
// First, get list of team members
const usersResponse = await fetch('/api/dashboard/users-for-stats/', {
    headers: {
        'Authorization': `Bearer ${accessToken}`
    }
});

const usersData = await usersResponse.json();
const selectedUser = usersData.users[0]; // Select first user

// Then get stats for that user
const statsResponse = await fetch(`/api/dashboard/project-work-stats/?user_id=${selectedUser.id}`, {
    headers: {
        'Authorization': `Bearer ${accessToken}`
    }
});

const statsData = await statsResponse.json();
```

## Calculation Logic

### Project Completion Percentage

For each project, the completion percentage is calculated as:

```
completion_percentage = (completed_tasks / total_tasks) * 100
```

Where:
- `completed_tasks`: Number of tasks with status = 'DONE'
- `total_tasks`: Total number of tasks in the project

### Overall Completion Percentage

The overall completion percentage across all projects is calculated as:

```
overall_percentage = (total_completed_tasks_all_projects / total_tasks_all_projects) * 100
```

This gives a weighted average based on the total number of tasks across all projects.

## Frontend Integration

### Dropdown Population

1. Call `/api/dashboard/users-for-stats/` to get the list of users
2. Populate a dropdown with the user list
3. When a user is selected, call `/api/dashboard/project-work-stats/?user_id={selected_user_id}`
4. Display the results in a pie chart and table

### Example React Component

```jsx
import React, { useState, useEffect } from 'react';

function ProjectWorkStats() {
    const [users, setUsers] = useState([]);
    const [selectedUserId, setSelectedUserId] = useState(null);
    const [stats, setStats] = useState(null);

    useEffect(() => {
        // Fetch users for dropdown
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

    useEffect(() => {
        if (selectedUserId) {
            // Fetch stats for selected user
            fetch(`/api/dashboard/project-work-stats/?user_id=${selectedUserId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            })
            .then(res => res.json())
            .then(data => setStats(data));
        }
    }, [selectedUserId]);

    return (
        <div>
            <select 
                value={selectedUserId} 
                onChange={(e) => setSelectedUserId(e.target.value)}
            >
                {users.map(user => (
                    <option key={user.id} value={user.id}>
                        {user.name}
                    </option>
                ))}
            </select>

            {stats && (
                <div>
                    <h3>Overall Completion: {stats.overall_completion_percentage}%</h3>
                    <ul>
                        {stats.projects.map(project => (
                            <li key={project.id}>
                                {project.name}: {project.completion_percentage}%
                                ({project.completed_tasks}/{project.total_tasks} tasks)
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}
```

## Notes

- Only projects where the user is set as `handled_by` are included in the statistics
- Projects with no tasks will not be included in the calculations
- The completion percentage is rounded to the nearest integer
- All user roles can access these endpoints with appropriate permission checks
- Statistics are calculated in real-time based on the current task statuses
