# Project Analytics API Documentation

## Overview

The Project Analytics Backend provides multi-level filtering for admin analytics dashboards. It supports 5 distinct filtering scenarios to track planned vs. achieved hours across projects, tasks, and employees.

**Base URL**: `/api/project-analytics/`

**Authentication**: Required (JWT token)

---

## Core Concepts

### Data Tracking
- **Planned Hours**: Set during task creation (stored in `Task.planned_hours`)
- **Achieved Hours**: Sum of all work sessions in ActivityLog for a task (multiple sessions accumulate)
- **Progress**: Calculated as `(achieved_hours / planned_hours) * 100%`

### Filtering Scenarios

| Scenario | Project | Employee | Use Case |
|----------|---------|----------|----------|
| **1. View All** | None | None | Admin dashboard showing all projects |
| **2. Project Only** | ✓ | None | Drill into one project's details |
| **3. Employee Only** | None | ✓ | View one employee's workload |
| **4. Project → Employee** | ✓ | ✓ | Specific employee's work in a project |
| **5. Employee → Project** | ✓ | ✓ | Same as #4 (cascading filter) |

---

## Endpoints

### 1. GET `/api/project-analytics/projects/`

Get projects with planned/achieved hours aggregated from tasks.

#### Query Parameters
| Parameter | Type | Required | Example | Scenario |
|-----------|------|----------|---------|----------|
| `project_id` | Integer | No | `?project_id=1` | Scenario 2, 4 |
| `employee_id` | Integer | No | `?employee_id=5` | Scenario 3, 4, 5 |
| Both | Both | No | `?project_id=1&employee_id=5` | Scenario 4, 5 |

#### Examples

**Scenario 1: View All Projects**
```bash
GET /api/project-analytics/projects/
```

**Scenario 2: Select Project Only**
```bash
GET /api/project-analytics/projects/?project_id=1
```

**Scenario 3: Select Employee Only**
```bash
GET /api/project-analytics/projects/?employee_id=5
```

**Scenario 4&5: Select Project AND Employee**
```bash
GET /api/project-analytics/projects/?project_id=1&employee_id=5
```

#### Response Format
```json
{
  "count": 2,
  "results": [
    {
      "id": 1,
      "name": "Mobile App Development",
      "status": "ACTIVE",
      "start_date": "2024-01-01",
      "due_date": "2024-12-31",
      "planned_hours": 500.0,
      "achieved_hours": 320.5,
      "progress": 64,
      "task_count": 8,
      "project_lead": "john@company.com"
    },
    {
      "id": 2,
      "name": "Backend Infrastructure",
      "status": "ACTIVE",
      "start_date": "2024-01-15",
      "due_date": "2024-09-30",
      "planned_hours": 400.0,
      "achieved_hours": 150.0,
      "progress": 37,
      "task_count": 5,
      "project_lead": "mike@company.com"
    }
  ],
  "filters": {
    "project_id": null,
    "employee_id": null
  }
}
```

---

### 2. GET `/api/project-analytics/tasks/`

Get tasks with planned/achieved hours and assignee information.

#### Query Parameters
| Parameter | Type | Required | Example |
|-----------|------|----------|---------|
| `project_id` | Integer | No | `?project_id=1` |
| `employee_id` | Integer | No | `?employee_id=5` |
| Both | Both | No | `?project_id=1&employee_id=5` |

#### Examples

**Get All Tasks**
```bash
GET /api/project-analytics/tasks/
```

**Get Tasks in a Project**
```bash
GET /api/project-analytics/tasks/?project_id=1
```

**Get Tasks Assigned to an Employee**
```bash
GET /api/project-analytics/tasks/?employee_id=5
```

**Get Employee's Tasks in a Specific Project**
```bash
GET /api/project-analytics/tasks/?project_id=1&employee_id=5
```

#### Response Format
```json
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "title": "Design UI Components",
      "project_id": 1,
      "project_name": "Mobile App Development",
      "status": "IN_PROGRESS",
      "priority": "HIGH",
      "planned_hours": 40.0,
      "achieved_hours": 32.5,
      "progress": 81,
      "start_date": "2024-01-10",
      "due_date": "2024-02-10",
      "assignees": [
        {
          "id": 5,
          "email": "dev1@company.com",
          "role": "DEV"
        },
        {
          "id": 6,
          "email": "dev2@company.com",
          "role": "DEV"
        }
      ]
    },
    {
      "id": 2,
      "title": "Implement API Endpoints",
      "project_id": 1,
      "project_name": "Mobile App Development",
      "status": "IN_PROGRESS",
      "priority": "CRITICAL",
      "planned_hours": 80.0,
      "achieved_hours": 45.0,
      "progress": 56,
      "start_date": "2024-01-15",
      "due_date": "2024-03-01",
      "assignees": [
        {
          "id": 7,
          "email": "backend@company.com",
          "role": "BACKEND"
        }
      ]
    }
  ],
  "filters": {
    "project_id": "1",
    "employee_id": null
  }
}
```

---

### 3. GET `/api/project-analytics/employees-for-project/`

Get employees assigned to a specific project (for dropdown filtering in UI).

**Used in Scenario 2**: When user selects a project, show team members dropdown.

#### Query Parameters
| Parameter | Type | Required | Example |
|-----------|------|----------|---------|
| `project_id` | Integer | **Yes** | `?project_id=1` |

#### Example
```bash
GET /api/project-analytics/employees-for-project/?project_id=1
```

#### Response Format
```json
{
  "count": 4,
  "project_id": 1,
  "project_name": "Mobile App Development",
  "results": [
    {
      "id": 5,
      "email": "dev1@company.com",
      "name": "dev1",
      "role": "EMPLOYEE",
      "task_count": 3
    },
    {
      "id": 6,
      "email": "dev2@company.com",
      "name": "dev2",
      "role": "EMPLOYEE",
      "task_count": 2
    },
    {
      "id": 7,
      "email": "backend@company.com",
      "name": "backend",
      "role": "EMPLOYEE",
      "task_count": 4
    },
    {
      "id": 8,
      "email": "design@company.com",
      "name": "design",
      "role": "EMPLOYEE",
      "task_count": 1
    }
  ]
}
```

---

### 4. GET `/api/project-analytics/projects-for-employee/`

Get projects assigned to a specific employee (for dropdown filtering in UI).

**Used in Scenario 3**: When user selects an employee, show their projects dropdown.

#### Query Parameters
| Parameter | Type | Required | Example |
|-----------|------|----------|---------|
| `employee_id` | Integer | **Yes** | `?employee_id=5` |

#### Example
```bash
GET /api/project-analytics/projects-for-employee/?employee_id=5
```

#### Response Format
```json
{
  "count": 3,
  "employee_id": 5,
  "employee_email": "dev1@company.com",
  "results": [
    {
      "id": 1,
      "name": "Mobile App Development",
      "status": "ACTIVE",
      "start_date": "2024-01-01",
      "due_date": "2024-12-31",
      "task_count": 3,
      "project_lead": "john@company.com"
    },
    {
      "id": 2,
      "name": "Backend Infrastructure",
      "status": "ACTIVE",
      "start_date": "2024-01-15",
      "due_date": "2024-09-30",
      "task_count": 2,
      "project_lead": "mike@company.com"
    },
    {
      "id": 3,
      "name": "Frontend Refactoring",
      "status": "ACTIVE",
      "start_date": "2024-02-01",
      "due_date": "2024-05-31",
      "task_count": 1,
      "project_lead": "sarah@company.com"
    }
  ]
}
```

---

## Usage Scenarios

### Scenario 1: View All (No Filters)

**Step 1**: Get all projects
```bash
GET /api/project-analytics/projects/
```

Returns all active projects with aggregated planned/achieved hours.

**Response**: List of all projects sorted by name

---

### Scenario 2: Select Project Only

**Step 1**: User selects a project from dropdown
```bash
GET /api/project-analytics/projects/?project_id=1
```

**Step 2**: Get employees in this project (to show team members dropdown)
```bash
GET /api/project-analytics/employees-for-project/?project_id=1
```

**Step 3**: (Optional) Get tasks in the project
```bash
GET /api/project-analytics/tasks/?project_id=1
```

**Response**: Project details, team members, and all tasks in the project

---

### Scenario 3: Select Employee Only

**Step 1**: User selects an employee from dropdown
```bash
GET /api/project-analytics/projects/?employee_id=5
```

**Step 2**: Get projects for this employee (to show projects dropdown)
```bash
GET /api/project-analytics/projects-for-employee/?employee_id=5
```

**Step 3**: (Optional) Get all tasks for this employee
```bash
GET /api/project-analytics/tasks/?employee_id=5
```

**Response**: Employee's projects and their assigned tasks across all projects

---

### Scenario 4: Select Project → Then Employee (Cascading)

**Step 1**: User selects a project
```bash
GET /api/project-analytics/projects/?project_id=1
```

**Step 2**: Get employees in this project
```bash
GET /api/project-analytics/employees-for-project/?project_id=1
```

**Step 3**: User selects an employee - Get filtered data
```bash
GET /api/project-analytics/projects/?project_id=1&employee_id=5
```

**Step 4**: (Optional) Get employee's tasks in this project
```bash
GET /api/project-analytics/tasks/?project_id=1&employee_id=5
```

**Response**: Employee's specific work in the selected project

---

### Scenario 5: Select Employee → Then Project (Cascading)

**Step 1**: User selects an employee
```bash
GET /api/project-analytics/projects/?employee_id=5
```

**Step 2**: Get projects for this employee
```bash
GET /api/project-analytics/projects-for-employee/?employee_id=5
```

**Step 3**: User selects a project - Get filtered data
```bash
GET /api/project-analytics/projects/?project_id=1&employee_id=5
```

**Step 4**: (Optional) Get employee's tasks in this project
```bash
GET /api/project-analytics/tasks/?project_id=1&employee_id=5
```

**Response**: Same as Scenario 4 (both orders produce identical results)

---

## Key Features

### Multi-Level Filtering
- **Independent**: Scenario 1 (no filters), Scenario 2 (project), Scenario 3 (employee)
- **Cascading**: Scenarios 4 & 5 (both filters, same result regardless of order)

### Cascading Dropdowns
- Filter Projects → Show Team Members in Project
- Filter Employee → Show Projects Employee Works On
- Filter Employee → Filter Project → Show Tasks

### Hours Aggregation
- **Planned Hours**: Sum of task `planned_hours` fields
- **Achieved Hours**: Sum of `hours_worked` from ActivityLog entries (multiple sessions)
- **Progress**: Calculated percentage based on ratio

### Data Relationships
- Projects → Tasks → ActivityLog (work sessions)
- Tasks → TaskAssignee (employee assignments)
- Multiple employees can be assigned to one task
- One employee can work on multiple tasks across projects

---

## Error Handling

### Invalid Project ID
```json
{
  "error": "Project not found"
}
```
Status: `404 NOT FOUND`

### Invalid Employee ID
```json
{
  "error": "Employee not found"
}
```
Status: `404 NOT FOUND`

### Missing Required Parameters
```json
{
  "error": "project_id query parameter is required"
}
```
Status: `400 BAD REQUEST`

### Unauthorized Access
```json
{
  "detail": "Authentication credentials were not provided."
}
```
Status: `401 UNAUTHORIZED`

---

## Performance Considerations

- All endpoints filter on **ACTIVE** projects only
- Cascading filters reduce returned data (employee-specific queries are faster)
- Hours aggregation is computed in-memory after filtering
- Consider implementing pagination for large datasets

---

## Integration with Frontend

### For Flutter Dashboard

1. **Load Initial Data**
   ```
   GET /project-analytics/projects/  → Show all projects
   ```

2. **Project Dropdown Selection**
   ```
   GET /project-analytics/employees-for-project/?project_id=X → Populate team dropdown
   ```

3. **Employee Dropdown Selection**
   ```
   GET /project-analytics/projects-for-employee/?employee_id=Y → Populate project dropdown
   ```

4. **Apply Filters**
   ```
   GET /project-analytics/projects/?project_id=X&employee_id=Y → Load filtered data
   GET /project-analytics/tasks/?project_id=X&employee_id=Y → Load task details
   ```

---

## Testing the Implementation

### Test Database Setup
Ensure you have:
- At least 2 active projects
- Multiple tasks per project with `planned_hours` set
- Multiple employees assigned to tasks
- ActivityLog entries with `hours_worked` recorded

### Sample cURL Commands

**Test Scenario 1: View All**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/project-analytics/projects/"
```

**Test Scenario 2: Project Only**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/project-analytics/projects/?project_id=1"
```

**Test Scenario 3: Employee Only**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/project-analytics/projects/?employee_id=5"
```

**Test Scenarios 4&5: Both Filters**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/project-analytics/projects/?project_id=1&employee_id=5"
```

**Test Cascading - Get Team In Project**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/project-analytics/employees-for-project/?project_id=1"
```

**Test Cascading - Get Projects For Employee**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/project-analytics/projects-for-employee/?employee_id=5"
```

---

## Implementation Status

✅ **Completed Features**:
- ProjectAnalyticsViewSet created with all 5 filtering scenarios
- `projects/` endpoint with multi-level filtering
- `tasks/` endpoint with multi-level filtering
- `employees-for-project/` endpoint for cascading dropdowns
- `projects-for-employee/` endpoint for cascading dropdowns
- Endpoints registered in URL router
- Proper error handling and validation
- Hours aggregation from ActivityLog

**Next Steps** (if needed):
- Frontend integration in Flutter Dashboard
- Pagination for large datasets
- Caching for performance optimization
- Real-time hour tracking updates
