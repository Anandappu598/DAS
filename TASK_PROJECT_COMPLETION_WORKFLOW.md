# Task and Project Completion Workflow

## Overview
The DAS backend manages a hierarchical workflow where **Projects** contain **Tasks**, which contain **Subtasks (Milestones)**. Completion is tracked at all levels with role-based permissions.

---

## 1. PROJECT LIFECYCLE

### Project Statuses
```
ACTIVE  ──→  COMPLETED
    ├─→ ON HOLD
    └─→ Back to ACTIVE
```

### Project Fields
| Field | Purpose | Notes |
|-------|---------|-------|
| `name` | Project title | Max 100 chars |
| `status` | Project state | ACTIVE, COMPLETED, ON HOLD |
| `start_date` | Project start | Date field |
| `due_date` | Project deadline | Date field |
| `completed_date` | Completion date | NULL until completed, then set to current date |
| `project_lead` | Primary lead | Can be NULL |
| `handled_by` | Responsible user | Required, cannot be NULL |
| `created_by` | Creator | Optional, for audit trail |
| `assignees` | Team members | Many-to-many relationship |
| `working_hours` | Total hours budgeted | Integer field |
| `duration` | Days to complete | Calculated: (due_date - start_date) |
| `description` | Project details | Text field |
| `is_approved` | Admin approval | Boolean, default False |
| `approval_status` | Approval state | PENDING_COMPLETION, etc |

### Project Completion Process

```
Step 1: CREATE PROJECT
├─ Set name, description, dates
├─ Assign project_lead and handled_by
├─ Set status = ACTIVE
└─ Optional: Add assignees

Step 2: CREATE TASKS (within active project)
├─ Create multiple tasks linked to project
├─ Each task has own status (PENDING → IN_PROGRESS → DONE)
└─ Set due dates for tasks

Step 3: MONITOR PROGRESS
├─ Track task completion percentage
├─ Dashboard shows: X/Y tasks done
└─ Update project metrics

Step 4: MARK PROJECT COMPLETE
├─ When ALL tasks are DONE
├─ Set status = COMPLETED
├─ Set completed_date = TODAY
└─ Record completion for analytics
```

### Who Can Create Projects?
- **ADMIN**: All projects
- **MANAGER**: Projects for their hierarchy
- **TEAMLEAD**: Projects for their team
- **EMPLOYEE**: Typically in their own projects

---

## 2. TASK LIFECYCLE

### Task Statuses
```
PENDING ──→ IN_PROGRESS ──→ DONE
    ├─────────────────────────────┘
    └─→ PENDING_APPROVAL ──→ (Approved: DONE / Rejected: IN_PROGRESS)
```

### Task Types
```
┌─────────────────────────────────────┐
│        TASK TYPES                   │
├─────────────────────────────────────┤
│ 1. STANDARD                         │
│    • One-time task                  │
│    • Has GitHub/Figma links         │
│    • Contains milestones (subtasks) │
│                                     │
│ 2. RECURRING                        │
│    • Repeats on pattern             │
│    • Patterns: DAILY, WEEKLY,       │
│               MONTHLY, YEARLY       │
│    • Auto-creates next instance     │
│                                     │
│ 3. ROUTINE                          │
│    • Regular maintenance tasks      │
│    • No milestones or links         │
│    • Simple tracking               │
└─────────────────────────────────────┘
```

### Task Priority Levels
- **LOW** - Non-urgent
- **MEDIUM** - Standard (default)
- **HIGH** - Important
- **CRITICAL** - Urgent

### Task Fields
| Field | Purpose | Notes |
|-------|---------|-------|
| `title` | Task name | Max 150 chars |
| `project` | Parent project | Foreign key, required |
| `status` | Current state | PENDING, IN_PROGRESS, DONE, PENDING_APPROVAL |
| `priority` | Relative importance | LOW, MEDIUM, HIGH, CRITICAL |
| `task_type` | Type of task | STANDARD, RECURRING, ROUTINE |
| `start_date` | When work begins | Optional, can be NULL |
| `due_date` | Deadline | Required, date field |
| `completed_at` | Actual completion date | NULL until task is DONE |
| `project_lead` | Task owner | Optional, can be NULL |
| `approval_status` | Approval state | For completion verification |
| `github_link` | Development link | URL field, optional |
| `figma_link` | Design link | URL field, optional |
| `next_occurrence` | For recurring tasks | Next execution date |
| `recurrence_pattern` | For recurring tasks | DAILY, WEEKLY, MONTHLY, YEARLY |

### Task Completion Process

```
Step 1: TASK ASSIGNMENT
├─ Create task with status: PENDING
├─ Assign task to users (TaskAssignee model)
│  └─ Each user has a role: LEAD, DEV, BACKEND
├─ Add milestones/subtasks (SubTask model)
│  └─ Each subtask: status (PENDING/IN_PROGRESS/DONE)
└─ Optional: Add GitHub/Figma links

Step 2: START TASK
├─ Change status: IN_PROGRESS
├─ Set start_date = TODAY (if NULL)
└─ Notify assignees

Step 3: TRACK SUBTASK PROGRESS
├─ For each subtask/milestone:
│  ├─ Update its status
│  └─ Track progress weight (importance %)
├─ System calculates TASK PROGRESS:
│  └─ Progress = (Completed Subtasks / Total Subtasks) × 100
└─ Example: If 2/4 subtasks done = 50% progress

Step 4: COMPLETE ALL SUBTASKS
├─ Mark ALL subtasks as DONE
└─ Task progress becomes 100%

Step 5: MARK TASK COMPLETE
├─ Change status: DONE
├─ Set completed_at = TODAY
├─ Optional: Request approval if needed
│  └─ Status: PENDING_APPROVAL
│  └─ Admin reviews and approves/rejects
│  └─ If rejected: status back to IN_PROGRESS
└─ Task completion recorded in DB
```

### Progress Calculation Logic

```python
def calculate_progress(task):
    subtasks = task.subtasks.all()
    count = subtasks.count()
    
    if count == 0:
        # No subtasks: check if task itself is DONE
        return 100 if task.status == 'DONE' else 0
    
    # With subtasks: percentage based on completion
    completed = subtasks.filter(status='DONE').count()
    return (completed / count) * 100
```

**Examples:**
- Task with 0 subtasks, status=DONE → Progress: 100%
- Task with 4 subtasks, 2 done → Progress: 50%
- Task with 4 subtasks, 0 done → Progress: 0%

### Recurring Task Workflow

```
Step 1: CREATE RECURRING TASK
├─ Set task_type: RECURRING
├─ Set recurrence_pattern: DAILY/WEEKLY/MONTHLY/YEARLY
├─ Set next_occurrence: Initial date
└─ Set start_date, due_date

Step 2: DAILY/WEEKLY/MONTHLY CHECK
├─ When task is marked DONE
├─ System auto-generates next instance:
│  ├─ If DAILY: next_date = today + 1 day
│  ├─ If WEEKLY: next_date = today + 7 days
│  ├─ If MONTHLY: next_date = today + 1 month
│  └─ If YEARLY: next_date = today + 1 year
└─ New task created with same config

Step 3: CONTINUOUS LOOP
├─ New instance: status = PENDING
├─ Assignees and subtasks copied from template
├─ Cycle repeats indefinitely
└─ Each instance tracked separately
```

---

## 3. SUBTASK (MILESTONE) SYSTEM

### SubTask Fields
```
├─ task (ForeignKey to Task)
├─ title (Milestone name)
├─ status (PENDING, IN_PROGRESS, DONE)
├─ progress_weight (Relative importance %)
│  └─ Example: If 4 milestones = 25% each
├─ due_date (When should be done)
└─ created_at (Timestamp)
```

### How Milestones Drive Task Completion

```
TASK: "Build Payment System"
├─ Milestone 1: "API Endpoint" (25%)
│  └─ Status: DONE ✓
├─ Milestone 2: "Database Schema" (25%)
│  └─ Status: DONE ✓
├─ Milestone 3: "Frontend Integration" (25%)
│  └─ Status: IN_PROGRESS
├─ Milestone 4: "Testing" (25%)
│  └─ Status: PENDING

CALCULATION:
  Completed: 2/4 = 50%
  Task Progress: 50%
  
AFTER ALL DONE:
  Completed: 4/4 = 100%
  Task Status: DONE
  Task completed_at: <TODAY>
```

---

## 4. ROLE-BASED ACCESS CONTROL

### Project Access Hierarchy

```
ADMIN
├─ Can see: ALL projects
├─ Can create: ANY project
├─ Can complete: ANY project
└─ Can assign: ANY users

MANAGER
├─ Can see: Projects where they or subordinates are involved
│  ├─ Where they are project_lead
│  ├─ Where they are handled_by
│  ├─ Where they created it
│  └─ Where subordinates are involved
├─ Can create: For their hierarchy
├─ Can complete: Their projects
└─ Can assign: Users in their hierarchy

TEAMLEAD
├─ Can see: Projects for team members
│  ├─ Where they are project_lead
│  ├─ Where they are handled_by
│  ├─ Where team members are involved
│  └─ Where they created it
├─ Can create: For their team
├─ Can complete: Team projects
└─ Can assign: Team members

EMPLOYEE
├─ Can see: Only their own projects
│  ├─ Where they are project_lead
│  ├─ Where they are handled_by
│  ├─ Where they created it
│  └─ Where they have task assignments
├─ Can create: Own projects
├─ Can complete: Own projects
└─ Can assign: Self (typically)
```

### Task Access Hierarchy (Similar Pattern)

```
ADMIN: All tasks

MANAGER: Tasks where manager or subordinates involved
- Directly assigned
- Created by them
- Created by subordinates
- Team members assigned

TEAMLEAD: Tasks for team members
- Where team lead is involved
- Where team members assigned
- Created by team lead

EMPLOYEE: Own tasks only
- Assigned to them
- Created by them
- Where marked as project_lead
```

---

## 5. TASK ASSIGNMENT MODEL

### TaskAssignee Relationship
```
Task (1) ──→ (Many) TaskAssignee (Many) ──→ (1) User

Example:
Task: "Build API"
├─ User: john@company.com (Role: LEAD)
├─ User: jane@company.com (Role: DEV)
└─ User: bob@company.com (Role: BACKEND)

Fields:
├─ task (ForeignKey)
├─ user (ForeignKey)
├─ role (LEAD, DEV, BACKEND)
└─ assigned_at (Timestamp)
```

### Unique Constraint
```
Each task-user pair is UNIQUE
↓
Same task cannot be assigned to same user twice
↓
Prevents duplicate assignments
```

---

## 6. APPROVAL SYSTEM

### ApprovalRequest Model
```
┌─────────────────────────────────────┐
│      APPROVAL REQUEST WORKFLOW       │
├─────────────────────────────────────┤
│ Reference Type: PROJECT / TASK      │
│ Approval Type:                      │
│ • CREATION - First-time creation    │
│ • COMPLETION - Marking as complete  │
│ • MODIFICATION - Changes to record  │
│                                     │
│ Status:                             │
│ • PENDING - Awaiting review         │
│ • APPROVED - Admin approved         │
│ • REJECTED - Admin rejected         │
└─────────────────────────────────────┘
```

### Approval Process

```
Step 1: USER REQUESTS APPROVAL
├─ Create ApprovalRequest
├─ Set reference_type (PROJECT/TASK)
├─ Set approval_type (CREATION/COMPLETION/MODIFICATION)
└─ Set status: PENDING

Step 2: ADMIN REVIEWS
├─ Get ApprovalRequest
├─ Examine request_data and details
└─ Decide APPROVE or REJECT

Step 3: ADMIN RESPONDS
├─ Create ApprovalResponse
├─ Set action: APPROVED or REJECTED
├─ Optional: Add rejection_reason
└─ ApprovalResponse saves ApprovalRequest status

Step 4: AFTER DECISION
├─ If APPROVED:
│  └─ Project/Task marked DONE
│  └─ completed_date/completed_at set
├─ If REJECTED:
│  └─ Status reverts to IN_PROGRESS
│  └─ rejection_reason stored
│  └─ User can update and resubmit
```

---

## 7. DATA CAPTURED FOR LINE CHARTS

### Key Dates Used in Charts

#### Projects
```
Database Field: completed_date
├─ Set when: status changed to COMPLETED
├─ Format: DateField (YYYY-MM-DD)
├─ Null: Initially NULL
├─ Set to: Current date on completion
└─ Used for: Project completion chart aggregation

Line Chart Grouping:
├─ Jan 2026: 3 projects completed
├─ Feb 2026: 4 projects completed
├─ Mar 2026: 2 projects completed
```

#### Tasks
```
Database Field: completed_at
├─ Set when: status changed to DONE
├─ Format: DateField (YYYY-MM-DD)
├─ Null: Initially NULL
├─ Set to: Current date on completion
└─ Used for: Task completion chart aggregation

Line Chart Grouping:
├─ Jan 2026: 15 tasks completed
├─ Feb 2026: 22 tasks completed
├─ Mar 2026: 18 tasks completed
```

### Calculate Completion Statistics

```
QUERY FOR PROJECT CHART:
SELECT 
  DATE_TRUNC('month', completed_date) as month,
  COUNT(*) as completion_count
FROM schedular_projects
WHERE status = 'COMPLETED'
  AND completed_date BETWEEN start_date AND end_date
GROUP BY month
ORDER BY month

QUERY FOR TASK CHART:
SELECT 
  DATE_TRUNC('month', completed_at) as month,
  COUNT(*) as completion_count
FROM schedular_task
WHERE status = 'DONE'
  AND completed_at BETWEEN start_date AND end_date
GROUP BY month
ORDER BY month
```

---

## 8. CHART DATA RETRIEVAL WITH ROLE-BASED FILTERING

### Project Chart Endpoint: `/api/project-completion-chart/`

```python
# ADMIN sees all
queryset = Projects.objects.filter(
    completed_date__isnull=False,
    completed_date__gte=start_date,
    completed_date__lte=end_date
)

# MANAGER sees their hierarchy
subordinates = manager.get_all_subordinates()
queryset = queryset.filter(
    Q(project_lead=manager) |
    Q(handled_by=manager) |
    Q(project_lead__in=subordinates) |
    Q(handled_by__in=subordinates)
)

# TEAMLEAD sees team data
team_members = teamlead.get_team_members()
queryset = queryset.filter(
    Q(project_lead=teamlead) |
    Q(handled_by=teamlead) |
    Q(project_lead__in=team_members) |
    Q(handled_by__in=team_members)
)

# EMPLOYEE sees only themselves
queryset = queryset.filter(
    Q(project_lead=employee) |
    Q(handled_by=employee)
)
```

### Task Chart Endpoint: `/api/task-completion-chart/`

```python
# Similar filtering but for Task model
# Key difference: Filter by status='DONE' and completed_at field

queryset = Task.objects.filter(
    status='DONE',
    completed_at__isnull=False,
    completed_at__gte=start_date,
    completed_at__lte=end_date
)

# Then apply same role-based filtering
```

---

## 9. EXAMPLE WORKFLOW SCENARIO

### Real-World Example: E-Commerce Platform Project

```
┌─────────────────────────────────────────────────────────┐
│ PROJECT: "E-Commerce Platform Rebuild"                  │
│ Started: 2026-01-15                                     │
│ Due Date: 2026-03-15                                    │
│ Project Lead: Alice (alice@company.com)                 │
│ Handled By: Bob (bob@company.com)                       │
│ Status: ACTIVE → (plan to complete)                     │
└─────────────────────────────────────────────────────────┘

JANUARY 2026:
─────────────
Task 1: "Database Schema Design"
├─ Status: PENDING → IN_PROGRESS → DONE
├─ Assigned: Charlie (DEV), Diana (BACKEND)
├─ Milestones:
│  ├─ ✓ Create ERD
│  ├─ ✓ Normalize Tables
│  └─ ✓ Set Constraints
├─ Completed_at: 2026-01-25
└─ Progress: 100%

FEBRUARY 2026:
──────────────
Task 2: "API Development"
├─ Status: PENDING → IN_PROGRESS (still ongoing)
├─ Assigned: Eve (LEAD), Frank (DEV)
├─ Milestones:
│  ├─ ✓ Auth Endpoints
│  ├─ ✓ User Endpoints
│  ├─ ⊘ Product Endpoints (In Progress)
│  └─ ⊘ Order Endpoints (Pending)
├─ Progress: 50%
└─ Not yet completed

Task 3: "Frontend - User Dashboard"
├─ Status: PENDING → IN_PROGRESS → DONE
├─ Assigned: Grace (LEAD), Henry (DEV)
├─ Milestones:
│  ├─ ✓ Layout Design
│  ├─ ✓ Components
│  └─ ✓ Integration
├─ Completed_at: 2026-02-10
└─ Progress: 100%

MARCH 2026:
───────────
Task 2: "API Development" (Continued)
├─ Status: IN_PROGRESS → DONE
├─ Completed_at: 2026-03-08
└─ Progress: 100%

Task 4: "Testing & QA"
├─ Status: PENDING → IN_PROGRESS → DONE
├─ Completed_at: 2026-03-14
└─ Progress: 100%

PROJECT COMPLETION:
───────────────────
✓ All tasks DONE
├─ Task 1: ✓ (Jan 25)
├─ Task 2: ✓ (Mar 8)
├─ Task 3: ✓ (Feb 10)
└─ Task 4: ✓ (Mar 14)

Project Status: ACTIVE → COMPLETED
Project completed_date: 2026-03-14

CHART DATA:
───────────
Jan 2026: 1 project completed (this one)
Feb 2026: - (still in progress)
Mar 2026: 1 project completed (final one marked)

Actually, if we're tracking within the period:
If project closed on Mar 14: Counted in March data point
```

---

## 10. KEY METRICS TRACKED

### For Line Charts

```
Per Month:
├─ Number of projects marked COMPLETED
├─ Number of tasks marked DONE
├─ Timestamp: Aggregated by calendar month
│  └─ Format: "2026-Jan", "2026-Feb", etc.
└─ Full name: "January 2026", "February 2026"

Database Queries:
├─ Projects: WHERE completed_date BETWEEN month_start AND month_end
├─ Tasks: WHERE completed_at BETWEEN month_start AND month_end
└─ Count each group
```

### Per User/Role (Role-Based)

```
ADMIN Dashboard:
├─ Sees: All projects/tasks across entire organization
├─ Chart shows: Sum of all completions per month
└─ Value: Global productivity view

MANAGER Dashboard:
├─ Sees: Only hierarchical data
├─ Chart shows: Team productivity
└─ Value: Team performance tracking

TEAMLEAD Dashboard:
├─ Sees: Only team data
├─ Chart shows: Team output
└─ Value: Direct team accountability

EMPLOYEE Dashboard:
├─ Sees: Only personal data
├─ Chart shows: Personal completion history
└─ Value: Self-assessment and tracking
```

---

## 11. WORKFLOW SUMMARY DIAGRAM

```
                    PROJECT LIFECYCLE
                    ─────────────────

 ┌─────────────┐         ┌──────────────┐
 │ CREATE      │         │ TASKS WITHIN │
 │ PROJECT     ├────────→│ PROJECT      │
 │ Status:     │         │ Can create   │
 │ ACTIVE      │         │ once project │
 └─────────────┘         │ is ACTIVE    │
                         └──────┬───────┘
                                │
                        ┌───────▼────────┐
                        │ TASK           │
                        │ Status:        │
                        │ PENDING        │
                        └───────┬────────┘
                                │
          ┌─────────────────────┼──────────────────────┐
          │                     │                      │
    ┌─────▼─────┐        ┌──────▼──────┐      ┌───────▼──────┐
    │ START TASK │        │ ADD         │      │ ASSIGN USERS │
    │ Status:    │        │ SUBTASKS    │      │ with roles   │
    │ IN_PROGRESS│        │ (Milestones)│     │ LEAD, DEV,   │
    └─────┬─────┘        └──────┬──────┘      │ BACKEND      │
          │                     │              └───────┬──────┘
          └─────────────────────┼────────────────────────┘
                                │
                        ┌───────▼──────────┐
                        │ UPDATE PROGRESS  │
                        │ • Complete       │
                        │   Subtasks       │
                        │ • Track %        │
                        └───────┬──────────┘
                                │
                        ┌───────▼──────────┐
                        │ ALL SUBTASKS     │
                        │ DONE?            │
                        └───┬────────┬─────┘
                            │ NO     │ YES
                    ┌───────┘        └──────┐
                    │                       │
            ┌───────▼─────────────────┐   ┌─▼──────────────────┐
            │ CONTINUE UPDATING       │   │ MARK TASK DONE     │
            │ Progress monitored      │   │ Status: DONE       │
            │ Dashboard shows: X%     │   │ Set completed_at   │
            └───┬───────────────┬─────┘   └─┬──────────────────┘
                │               │           │
                └───────┬───────┘           │
                        │                   │
                        │         ┌─────────▼──────┐
                        │         │ REQUEST        │
                        │         │ APPROVAL?      │
                        │         └────┬───────┬───┘
                        │              │ NO    │ YES
                        │    ┌─────────┘       └─────┐
                        │    │                       │
                        │    │                  ┌────▼─────────┐
                        │    │                  │ PENDING_     │
                        │    │                  │ APPROVAL     │
                        │    │                  │ Await Admin  │
                        │    │                  └─┬──────────┬─┘
                        │    │                    │          │
                        │    │            ┌───────┘          └──┐
                        │    │            │ REJECTED            │
                        │    │            │ Reverts to          │
                        │    │            │ IN_PROGRESS         │
                        │    │            │                     │
                        │    │      ┌─────▼──────┐        ┌──────▼────┐
                        │    │      │ USER CAN   │        │ APPROVED   │
                        │    │      │ UPDATE &   │        │ Task       │
                        │    │      │ RESUBMIT   │        │ Complete   │
                        │    │      └─────┬──────┘        └─────┬──────┘
                        │    │            │                     │
                        │    └────────────┼─────────────────────┘
                        │                 │
                        │         ┌───────▼────────────────┐
                        │         │ TASK COMPLETION        │
                        │         │ RECORDED IN DB         │
                        │         │ completed_at: TODAY    │
                        │         └───────┬────────────────┘
                        │                 │
                        │         ┌───────▼──────────┐
                        │         │ ALL TASKS IN     │
                        │         │ PROJECT DONE?    │
                        │         └───┬────────┬─────┘
                        │             │ NO     │ YES
                        │    ┌────────┘        └───────┐
                        │    │                         │
                        └────┤                  ┌──────▼────────┐
                             │                  │ MARK PROJECT  │
                             │                  │ COMPLETE      │
                             │                  │ Status:       │
                             │    ┌─────────────│ COMPLETED     │
                             │    │             │ Set           │
                             │    │             │ completed_date│
                             └────┼─────────────└──┬────────────┘
                                  │                │
                        ┌─────────▼─────────────────▼─┐
                        │ LINE CHART DATA READY      │
                        │                             │
                        │ Jan 2026: 3 projects done  │
                        │ Feb 2026: 4 projects done  │
                        │ Mar 2026: 2 projects done  │
                        │                             │
                        │ Chart displays per month   │
                        │ based on role-based access │
                        └─────────────────────────────┘
```

---

## 12. IMPORTANT NOTES

### Completion Recording
✅ **Project**: Set `completed_date` when status → COMPLETED  
✅ **Task**: Set `completed_at` when status → DONE  
✅ Both must be populated for line chart aggregation

### Progress Calculation
- **Without Subtasks**: Task progress = 0% (PENDING/IN_PROGRESS), 100% if DONE
- **With Subtasks**: Task progress = (Completed / Total × 100%)
- **Project Progress**: Sum of all task progress / number of tasks

### Role Hierarchy
- ADMIN > MANAGER > TEAMLEAD > EMPLOYEE
- Each role sees different data in line charts
- Filtering happens at query level for efficiency

### Recurring Tasks
- Auto-generate next instance on completion
- Each instance is independent
- All instances tracked for metrics

### Approval System
- Optional: Not all completions require approval
- Configurable per organization needs
- Rejection allows resubmission

---

## Summary Table

| Aspect | Project | Task | Subtask |
|--------|---------|------|---------|
| **Statuses** | ACTIVE, COMPLETED, ON HOLD | PENDING, IN_PROGRESS, DONE, PENDING_APPROVAL | PENDING, IN_PROGRESS, DONE |
| **Types** | 1 type | 3 types (STANDARD, RECURRING, ROUTINE) | Fixed type |
| **Completion Field** | `completed_date` | `completed_at` | Status only |
| **Chart Aggregation** | By `completed_date` | By `completed_at` | Via parent task |
| **Progress Tracking** | Via tasks | Via subtasks | Direct |
| **Parent** | None | Project | Task |
| **Assignees** | Multiple (M2M) | Via TaskAssignee | None direct |

