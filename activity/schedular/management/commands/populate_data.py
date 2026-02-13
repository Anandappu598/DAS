from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, time, timedelta
from schedular.models import (
    User, Department, OTPVerification, Projects, ApprovalRequest, 
    ApprovalResponse, Task, TaskAssignee, SubTask, TeamInstruction,
    Notification, QuickNote, Catalog, TodayPlan, ActivityLog, 
    Pending, DaySession
)
import random


class Command(BaseCommand):
    help = 'Populate all database tables with sample data'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Starting data population...'))

        # Check if basic data already exists
        if not User.objects.filter(email='admin@company.com').exists():
            # Create basic data
            self.create_departments()
            self.create_users()
            self.create_otp_verifications()
            self.create_projects()
            self.create_approval_requests()
            self.create_approval_responses()
            self.create_tasks()
            self.create_task_assignees()
            self.create_subtasks()
            self.create_team_instructions()
            self.create_notifications()
            self.create_quick_notes()
        else:
            self.stdout.write(self.style.SUCCESS('Basic data already exists, skipping...'))

        # Create catalog and activity data (can be created multiple times or check individually)
        if Catalog.objects.count() == 0:
            self.create_catalogs()
        else:
            self.stdout.write(self.style.SUCCESS('Catalog data already exists, skipping...'))
            
        if TodayPlan.objects.count() == 0:
            self.create_today_plans()
        else:
            self.stdout.write(self.style.SUCCESS('TodayPlan data already exists, skipping...'))
            
        if ActivityLog.objects.count() == 0:
            self.create_activity_logs()
        else:
            self.stdout.write(self.style.SUCCESS('ActivityLog data already exists, skipping...'))
            
        if Pending.objects.count() == 0:
            self.create_pending_tasks()
        else:
            self.stdout.write(self.style.SUCCESS('Pending data already exists, skipping...'))
            
        if DaySession.objects.count() == 0:
            self.create_day_sessions()
        else:
            self.stdout.write(self.style.SUCCESS('DaySession data already exists, skipping...'))

        self.stdout.write(self.style.SUCCESS('Successfully populated all tables!'))

    def clear_data(self):
        """Clear existing data from all tables"""
        self.stdout.write('Clearing existing data...')
        
        # Delete in reverse order of dependencies
        DaySession.objects.all().delete()
        Pending.objects.all().delete()
        ActivityLog.objects.all().delete()
        TodayPlan.objects.all().delete()
        Catalog.objects.all().delete()
        QuickNote.objects.all().delete()
        Notification.objects.all().delete()
        TeamInstruction.objects.all().delete()
        SubTask.objects.all().delete()
        TaskAssignee.objects.all().delete()
        Task.objects.all().delete()
        ApprovalResponse.objects.all().delete()
        ApprovalRequest.objects.all().delete()
        Projects.objects.all().delete()
        OTPVerification.objects.all().delete()
        User.objects.all().delete()
        Department.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS('Data cleared!'))

    def create_departments(self):
        """Create departments"""
        departments_data = [
            'Engineering',
            'Product Management',
            'Design',
            'Marketing',
            'Sales',
            'Human Resources',
            'Finance',
            'Customer Support'
        ]
        
        for dept_name in departments_data:
            Department.objects.get_or_create(name=dept_name)
        
        self.stdout.write(self.style.SUCCESS(f'Created/Retrieved {len(departments_data)} departments'))

    def create_users(self):
        """Create users with different roles"""
        departments = list(Department.objects.all())
        
        users_data = [
            {'email': 'admin@company.com', 'password': 'admin123', 'role': 'ADMIN', 'phone': '+1234567890'},
            {'email': 'manager1@company.com', 'password': 'manager123', 'role': 'MANAGER', 'phone': '+1234567891'},
            {'email': 'manager2@company.com', 'password': 'manager123', 'role': 'MANAGER', 'phone': '+1234567892'},
            {'email': 'teamlead1@company.com', 'password': 'lead123', 'role': 'TEAMLEAD', 'phone': '+1234567893'},
            {'email': 'teamlead2@company.com', 'password': 'lead123', 'role': 'TEAMLEAD', 'phone': '+1234567894'},
            {'email': 'emp1@company.com', 'password': 'emp123', 'role': 'EMPLOYEE', 'phone': '+1234567895'},
            {'email': 'emp2@company.com', 'password': 'emp123', 'role': 'EMPLOYEE', 'phone': '+1234567896'},
            {'email': 'emp3@company.com', 'password': 'emp123', 'role': 'EMPLOYEE', 'phone': '+1234567897'},
            {'email': 'emp4@company.com', 'password': 'emp123', 'role': 'EMPLOYEE', 'phone': '+1234567898'},
            {'email': 'emp5@company.com', 'password': 'emp123', 'role': 'EMPLOYEE', 'phone': '+1234567899'},
        ]
        
        for idx, user_data in enumerate(users_data):
            user, created = User.objects.get_or_create(
                email=user_data['email'],
                defaults={'role': user_data['role']}
            )
            if created:
                user.set_password(user_data['password'])
            user.phone_number = user_data['phone']
            user.department = departments[idx % len(departments)]
            user.theme_preference = random.choice(['light', 'dark', 'auto'])
            user.save()
        
        self.stdout.write(self.style.SUCCESS(f'Created/Retrieved {len(users_data)} users'))

    def create_otp_verifications(self):
        """Create OTP verification records"""
        otp_data = [
            {
                'email': 'newuser1@company.com',
                'otp_type': 'signup',
                'is_verified': False,
                'user_data': {'name': 'New User 1', 'role': 'EMPLOYEE'}
            },
            {
                'email': 'newuser2@company.com',
                'otp_type': 'signup',
                'is_verified': True,
                'user_data': {'name': 'New User 2', 'role': 'EMPLOYEE'}
            },
            {
                'email': 'emp1@company.com',
                'otp_type': 'forgot_password',
                'is_verified': False,
                'user_data': None
            },
        ]
        
        for data in otp_data:
            OTPVerification.objects.create(
                email=data['email'],
                otp=OTPVerification.generate_otp(),
                otp_type=data['otp_type'],
                is_verified=data['is_verified'],
                user_data=data['user_data']
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(otp_data)} OTP verification records'))

    def create_projects(self):
        """Create projects"""
        admin = User.objects.get(email='admin@company.com')
        manager1 = User.objects.get(email='manager1@company.com')
        manager2 = User.objects.get(email='manager2@company.com')
        teamlead1 = User.objects.get(email='teamlead1@company.com')
        teamlead2 = User.objects.get(email='teamlead2@company.com')
        
        projects_data = [
            {
                'name': 'E-Commerce Platform',
                'status': 'ACTIVE',
                'project_lead': teamlead1,
                'start_date': date.today() - timedelta(days=60),
                'due_date': date.today() + timedelta(days=90),
                'description': 'Building a modern e-commerce platform with advanced features',
                'working_hours': 8,
                'duration': 150,
                'handled_by': manager1,
                'created_by': admin,
                'is_approved': True
            },
            {
                'name': 'Mobile App Development',
                'status': 'ACTIVE',
                'project_lead': teamlead2,
                'start_date': date.today() - timedelta(days=30),
                'due_date': date.today() + timedelta(days=120),
                'description': 'Cross-platform mobile application for customer engagement',
                'working_hours': 8,
                'duration': 150,
                'handled_by': manager2,
                'created_by': admin,
                'is_approved': True
            },
            {
                'name': 'Data Analytics Dashboard',
                'status': 'ACTIVE',
                'project_lead': teamlead1,
                'start_date': date.today() - timedelta(days=15),
                'due_date': date.today() + timedelta(days=60),
                'description': 'Real-time analytics dashboard for business intelligence',
                'working_hours': 6,
                'duration': 75,
                'handled_by': manager1,
                'created_by': admin,
                'is_approved': True
            },
            {
                'name': 'API Gateway Implementation',
                'status': 'ON HOLD',
                'project_lead': teamlead2,
                'start_date': date.today() - timedelta(days=90),
                'due_date': date.today() + timedelta(days=30),
                'description': 'Microservices API gateway with authentication',
                'working_hours': 8,
                'duration': 120,
                'handled_by': manager2,
                'created_by': admin,
                'is_approved': True
            },
            {
                'name': 'Website Redesign',
                'status': 'COMPLETED',
                'project_lead': teamlead1,
                'start_date': date.today() - timedelta(days=120),
                'due_date': date.today() - timedelta(days=30),
                'completed_date': date.today() - timedelta(days=25),
                'description': 'Complete redesign of company website',
                'working_hours': 8,
                'duration': 90,
                'handled_by': manager1,
                'created_by': admin,
                'is_approved': True
            },
        ]
        
        for project_data in projects_data:
            Projects.objects.create(**project_data)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(projects_data)} projects'))

    def create_approval_requests(self):
        """Create approval requests"""
        projects = list(Projects.objects.all())
        manager1 = User.objects.get(email='manager1@company.com')
        teamlead1 = User.objects.get(email='teamlead1@company.com')
        emp1 = User.objects.get(email='emp1@company.com')
        
        requests_data = [
            {
                'reference_type': 'PROJECT',
                'reference_id': projects[0].id,
                'approval_type': 'CREATION',
                'requested_by': manager1,
                'status': 'APPROVED',
                'request_data': {'project_name': projects[0].name}
            },
            {
                'reference_type': 'PROJECT',
                'reference_id': projects[4].id,
                'approval_type': 'COMPLETION',
                'requested_by': teamlead1,
                'status': 'APPROVED',
                'request_data': {'project_name': projects[4].name}
            },
            {
                'reference_type': 'TASK',
                'reference_id': 1,
                'approval_type': 'CREATION',
                'requested_by': teamlead1,
                'status': 'PENDING',
                'request_data': {'task_title': 'New Feature Implementation'}
            },
            {
                'reference_type': 'TASK',
                'reference_id': 2,
                'approval_type': 'COMPLETION',
                'requested_by': emp1,
                'status': 'REJECTED',
                'request_data': {'task_title': 'Bug Fix'}
            },
        ]
        
        for request_data in requests_data:
            ApprovalRequest.objects.create(**request_data)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(requests_data)} approval requests'))

    def create_approval_responses(self):
        """Create approval responses"""
        admin = User.objects.get(email='admin@company.com')
        approved_requests = ApprovalRequest.objects.filter(status__in=['APPROVED', 'REJECTED'])
        
        for request in approved_requests:
            if request.status == 'APPROVED':
                ApprovalResponse.objects.create(
                    approval_request=request,
                    action='APPROVED',
                    reviewed_by=admin
                )
            else:
                ApprovalResponse.objects.create(
                    approval_request=request,
                    action='REJECTED',
                    reviewed_by=admin,
                    rejection_reason='Does not meet the quality standards'
                )
        
        self.stdout.write(self.style.SUCCESS(f'Created {approved_requests.count()} approval responses'))

    def create_tasks(self):
        """Create tasks"""
        projects = list(Projects.objects.filter(status='ACTIVE'))
        teamleads = list(User.objects.filter(role='TEAMLEAD'))
        
        tasks_data = [
            {
                'title': 'Design Database Schema',
                'project': projects[0],
                'project_lead': teamleads[0],
                'task_type': 'STANDARD',
                'priority': 'HIGH',
                'status': 'DONE',
                'start_date': date.today() - timedelta(days=50),
                'due_date': date.today() - timedelta(days=40),
                'completed_at': date.today() - timedelta(days=38),
                'github_link': 'https://github.com/company/ecommerce/issues/1',
            },
            {
                'title': 'Implement User Authentication',
                'project': projects[0],
                'project_lead': teamleads[0],
                'task_type': 'STANDARD',
                'priority': 'CRITICAL',
                'status': 'IN_PROGRESS',
                'start_date': date.today() - timedelta(days=20),
                'due_date': date.today() + timedelta(days=10),
                'github_link': 'https://github.com/company/ecommerce/issues/2',
            },
            {
                'title': 'Create Product Catalog UI',
                'project': projects[0],
                'project_lead': teamleads[0],
                'task_type': 'STANDARD',
                'priority': 'HIGH',
                'status': 'IN_PROGRESS',
                'start_date': date.today() - timedelta(days=15),
                'due_date': date.today() + timedelta(days=15),
                'figma_link': 'https://figma.com/file/product-catalog',
            },
            {
                'title': 'Setup Mobile App Framework',
                'project': projects[1],
                'project_lead': teamleads[1],
                'task_type': 'STANDARD',
                'priority': 'CRITICAL',
                'status': 'DONE',
                'start_date': date.today() - timedelta(days=25),
                'due_date': date.today() - timedelta(days=15),
                'completed_at': date.today() - timedelta(days=14),
            },
            {
                'title': 'Design Mobile UI/UX',
                'project': projects[1],
                'project_lead': teamleads[1],
                'task_type': 'STANDARD',
                'priority': 'HIGH',
                'status': 'IN_PROGRESS',
                'start_date': date.today() - timedelta(days=10),
                'due_date': date.today() + timedelta(days=20),
                'figma_link': 'https://figma.com/file/mobile-app',
            },
            {
                'title': 'Implement Push Notifications',
                'project': projects[1],
                'project_lead': teamleads[1],
                'task_type': 'STANDARD',
                'priority': 'MEDIUM',
                'status': 'PENDING',
                'start_date': None,
                'due_date': date.today() + timedelta(days=45),
            },
            {
                'title': 'Daily Standup Meeting',
                'project': projects[0],
                'project_lead': teamleads[0],
                'task_type': 'RECURRING',
                'priority': 'MEDIUM',
                'status': 'PENDING',
                'start_date': date.today(),
                'due_date': date.today(),
                'next_occurrence': date.today() + timedelta(days=1),
                'recurrence_pattern': 'DAILY',
            },
            {
                'title': 'Weekly Sprint Review',
                'project': projects[1],
                'project_lead': teamleads[1],
                'task_type': 'RECURRING',
                'priority': 'HIGH',
                'status': 'PENDING',
                'start_date': date.today(),
                'due_date': date.today() + timedelta(days=7),
                'next_occurrence': date.today() + timedelta(days=7),
                'recurrence_pattern': 'WEEKLY',
            },
            {
                'title': 'Setup Analytics Infrastructure',
                'project': projects[2],
                'project_lead': teamleads[0],
                'task_type': 'STANDARD',
                'priority': 'CRITICAL',
                'status': 'IN_PROGRESS',
                'start_date': date.today() - timedelta(days=10),
                'due_date': date.today() + timedelta(days=15),
                'github_link': 'https://github.com/company/analytics/issues/1',
            },
            {
                'title': 'Design Dashboard Widgets',
                'project': projects[2],
                'project_lead': teamleads[0],
                'task_type': 'STANDARD',
                'priority': 'HIGH',
                'status': 'PENDING',
                'start_date': None,
                'due_date': date.today() + timedelta(days=30),
                'figma_link': 'https://figma.com/file/analytics-dashboard',
            },
        ]
        
        for task_data in tasks_data:
            Task.objects.create(**task_data)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(tasks_data)} tasks'))

    def create_task_assignees(self):
        """Create task assignees"""
        tasks = list(Task.objects.filter(task_type='STANDARD'))
        employees = list(User.objects.filter(role='EMPLOYEE'))
        teamleads = list(User.objects.filter(role='TEAMLEAD'))
        
        # Assign employees to tasks
        for idx, task in enumerate(tasks[:6]):
            # Assign lead
            TaskAssignee.objects.create(
                task=task,
                user=teamleads[idx % len(teamleads)],
                role='LEAD'
            )
            
            # Assign developers
            for emp_idx in range(2):
                emp = employees[(idx + emp_idx) % len(employees)]
                TaskAssignee.objects.create(
                    task=task,
                    user=emp,
                    role=random.choice(['DEV', 'BACKEND'])
                )
        
        self.stdout.write(self.style.SUCCESS('Created task assignees'))

    def create_subtasks(self):
        """Create subtasks"""
        tasks = list(Task.objects.filter(task_type='STANDARD')[:5])
        
        subtasks_data = [
            # For task 1 (Database Schema) - DONE
            {'task': tasks[0], 'title': 'Design user tables', 'status': 'DONE', 'weight': 30},
            {'task': tasks[0], 'title': 'Design product tables', 'status': 'DONE', 'weight': 30},
            {'task': tasks[0], 'title': 'Design order tables', 'status': 'DONE', 'weight': 20},
            {'task': tasks[0], 'title': 'Create migrations', 'status': 'DONE', 'weight': 20},
            
            # For task 2 (User Authentication) - IN_PROGRESS
            {'task': tasks[1], 'title': 'Setup JWT authentication', 'status': 'DONE', 'weight': 30},
            {'task': tasks[1], 'title': 'Implement login endpoint', 'status': 'IN_PROGRESS', 'weight': 25},
            {'task': tasks[1], 'title': 'Implement registration endpoint', 'status': 'PENDING', 'weight': 25},
            {'task': tasks[1], 'title': 'Add password reset flow', 'status': 'PENDING', 'weight': 20},
            
            # For task 3 (Product Catalog UI)
            {'task': tasks[2], 'title': 'Create product grid layout', 'status': 'DONE', 'weight': 25},
            {'task': tasks[2], 'title': 'Implement product filter', 'status': 'IN_PROGRESS', 'weight': 25},
            {'task': tasks[2], 'title': 'Add search functionality', 'status': 'IN_PROGRESS', 'weight': 25},
            {'task': tasks[2], 'title': 'Implement pagination', 'status': 'PENDING', 'weight': 25},
            
            # For task 4 (Mobile Framework)
            {'task': tasks[3], 'title': 'Setup React Native', 'status': 'DONE', 'weight': 40},
            {'task': tasks[3], 'title': 'Configure navigation', 'status': 'DONE', 'weight': 30},
            {'task': tasks[3], 'title': 'Setup state management', 'status': 'DONE', 'weight': 30},
            
            # For task 5 (Mobile UI/UX)
            {'task': tasks[4], 'title': 'Design home screen', 'status': 'DONE', 'weight': 25},
            {'task': tasks[4], 'title': 'Design profile screen', 'status': 'IN_PROGRESS', 'weight': 25},
            {'task': tasks[4], 'title': 'Design settings screen', 'status': 'PENDING', 'weight': 25},
            {'task': tasks[4], 'title': 'Create reusable components', 'status': 'IN_PROGRESS', 'weight': 25},
        ]
        
        for data in subtasks_data:
            due_date = data['task'].due_date
            if data['status'] == 'DONE':
                completed_at = due_date - timedelta(days=random.randint(1, 10))
            else:
                completed_at = None
            
            SubTask.objects.create(
                task=data['task'],
                title=data['title'],
                status=data['status'],
                progress_weight=data['weight'],
                due_date=due_date,
                completed_at=completed_at
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(subtasks_data)} subtasks'))

    def create_team_instructions(self):
        """Create team instructions"""
        projects = list(Projects.objects.filter(status='ACTIVE'))
        teamleads = list(User.objects.filter(role='TEAMLEAD'))
        employees = list(User.objects.filter(role='EMPLOYEE'))
        
        instructions_data = [
            {
                'project': projects[0],
                'subject': 'Code Review Guidelines',
                'instructions': 'Please ensure all PRs are reviewed within 24 hours. Follow the coding standards document.',
                'sent_by': teamleads[0],
                'recipients': employees[:3]
            },
            {
                'project': projects[1],
                'subject': 'Sprint Planning Meeting',
                'instructions': 'Join the sprint planning meeting tomorrow at 10 AM. Please prepare your task estimates.',
                'sent_by': teamleads[1],
                'recipients': employees[3:]
            },
            {
                'project': projects[0],
                'subject': 'Security Best Practices',
                'instructions': 'Remember to sanitize all user inputs and use parameterized queries to prevent SQL injection.',
                'sent_by': teamleads[0],
                'recipients': employees[:4]
            },
        ]
        
        for data in instructions_data:
            instruction = TeamInstruction.objects.create(
                project=data['project'],
                subject=data['subject'],
                instructions=data['instructions'],
                sent_by=data['sent_by']
            )
            instruction.recipients.set(data['recipients'])
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(instructions_data)} team instructions'))

    def create_notifications(self):
        """Create notifications"""
        users = list(User.objects.all())
        projects = list(Projects.objects.all())
        tasks = list(Task.objects.all())
        
        notifications_data = [
            # Project notifications
            {
                'user': User.objects.get(email='manager1@company.com'),
                'notification_type': 'PROJECT_APPROVED',
                'title': 'Project Approved',
                'message': f'Your project "{projects[0].name}" has been approved by admin.',
                'reference_type': 'project',
                'reference_id': projects[0].id,
                'is_read': True
            },
            {
                'user': User.objects.get(email='teamlead1@company.com'),
                'notification_type': 'PROJECT_CREATED',
                'title': 'New Project Created',
                'message': f'You have been assigned as lead for "{projects[0].name}".',
                'reference_type': 'project',
                'reference_id': projects[0].id,
                'is_read': True
            },
            
            # Task notifications
            {
                'user': User.objects.get(email='emp1@company.com'),
                'notification_type': 'TASK_ASSIGNED',
                'title': 'New Task Assigned',
                'message': f'You have been assigned to "{tasks[0].title}".',
                'reference_type': 'task',
                'reference_id': tasks[0].id,
                'is_read': False
            },
            {
                'user': User.objects.get(email='emp2@company.com'),
                'notification_type': 'TASK_ASSIGNED',
                'title': 'New Task Assigned',
                'message': f'You have been assigned to "{tasks[1].title}".',
                'reference_type': 'task',
                'reference_id': tasks[1].id,
                'is_read': False
            },
            {
                'user': User.objects.get(email='teamlead1@company.com'),
                'notification_type': 'TASK_COMPLETED',
                'title': 'Task Completed',
                'message': f'Task "{tasks[0].title}" has been marked as completed.',
                'reference_type': 'task',
                'reference_id': tasks[0].id,
                'is_read': True
            },
            
            # Approval notifications
            {
                'user': User.objects.get(email='admin@company.com'),
                'notification_type': 'APPROVAL_REQUESTED',
                'title': 'Approval Required',
                'message': 'A new project approval request is pending your review.',
                'reference_type': 'approval',
                'reference_id': 1,
                'is_read': False
            },
            
            # Instruction notifications
            {
                'user': User.objects.get(email='emp1@company.com'),
                'notification_type': 'INSTRUCTION_RECEIVED',
                'title': 'New Team Instruction',
                'message': 'You have received new instructions for Code Review Guidelines.',
                'reference_type': 'instruction',
                'reference_id': 1,
                'is_read': False
            },
            {
                'user': User.objects.get(email='emp3@company.com'),
                'notification_type': 'SUBTASK_COMPLETED',
                'title': 'Subtask Completed',
                'message': 'Subtask "Setup JWT authentication" has been completed.',
                'reference_type': 'subtask',
                'reference_id': 1,
                'is_read': True
            },
        ]
        
        for data in notifications_data:
            Notification.objects.create(**data)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(notifications_data)} notifications'))

    def create_quick_notes(self):
        """Create quick notes"""
        employees = list(User.objects.filter(role='EMPLOYEE'))
        
        notes_data = [
            'Remember to update documentation after completing the feature',
            'Bug in payment gateway - needs investigation',
            'Meeting notes: Discussed new API endpoints',
            'Code review feedback: Improve error handling',
            'Performance optimization ideas for database queries',
        ]
        
        for idx, note_text in enumerate(notes_data):
            QuickNote.objects.create(
                user=employees[idx % len(employees)],
                note_text=note_text
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(notes_data)} quick notes'))

    def create_catalogs(self):
        """Create catalog items"""
        projects = list(Projects.objects.all())
        tasks = list(Task.objects.all())
        users = list(User.objects.filter(role='EMPLOYEE'))
        
        catalogs_data = [
            # Project-based catalogs
            {
                'user': users[0],
                'name': projects[0].name,
                'description': projects[0].description,
                'catalog_type': 'PROJECT',
                'project': projects[0],
                'estimated_hours': float(projects[0].working_hours * projects[0].duration),
                'progress_percentage': 45
            },
            {
                'user': users[1],
                'name': projects[1].name,
                'description': projects[1].description,
                'catalog_type': 'PROJECT',
                'project': projects[1],
                'estimated_hours': float(projects[1].working_hours * projects[1].duration),
                'progress_percentage': 30
            },
            
            # Task-based catalogs
            {
                'user': users[0],
                'name': tasks[1].title,
                'description': 'Building authentication system',
                'catalog_type': 'TASK',
                'task': tasks[1],
                'estimated_hours': 40.0,
                'progress_percentage': 50
            },
            {
                'user': users[2],
                'name': tasks[2].title,
                'description': 'Creating product catalog interface',
                'catalog_type': 'TASK',
                'task': tasks[2],
                'estimated_hours': 32.0,
                'progress_percentage': 40
            },
            
            # Course catalogs
            {
                'user': users[0],
                'name': 'Advanced Python Programming',
                'description': 'Learning advanced Python concepts and best practices',
                'catalog_type': 'COURSE',
                'estimated_hours': 20.0,
                'progress_percentage': 60
            },
            {
                'user': users[1],
                'name': 'React Native Masterclass',
                'description': 'Complete guide to React Native development',
                'catalog_type': 'COURSE',
                'estimated_hours': 30.0,
                'progress_percentage': 35
            },
            
            # Routine catalogs
            {
                'user': users[0],
                'name': 'Daily Code Review',
                'description': 'Review team pull requests',
                'catalog_type': 'ROUTINE',
                'estimated_hours': 1.0,
                'progress_percentage': 100
            },
            {
                'user': users[2],
                'name': 'Email Management',
                'description': 'Check and respond to emails',
                'catalog_type': 'ROUTINE',
                'estimated_hours': 0.5,
                'progress_percentage': 100
            },
            
            # Custom work
            {
                'user': users[1],
                'name': 'Research New Technologies',
                'description': 'Exploring new frameworks and tools',
                'catalog_type': 'CUSTOM',
                'estimated_hours': 10.0,
                'progress_percentage': 20
            },
        ]
        
        for data in catalogs_data:
            Catalog.objects.create(**data)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(catalogs_data)} catalog items'))

    def create_today_plans(self):
        """Create today's plan items"""
        catalogs = list(Catalog.objects.all())
        users = list(User.objects.filter(role='EMPLOYEE'))
        
        today = date.today()
        
        plans_data = [
            # User 1 plans
            {
                'user': users[0],
                'catalog_item': catalogs[0],
                'plan_date': today,
                'scheduled_start_time': time(9, 0),
                'scheduled_end_time': time(11, 0),
                'planned_duration_minutes': 120,
                'quadrant': 'Q1',
                'order_index': 0,
                'status': 'COMPLETED'
            },
            {
                'user': users[0],
                'catalog_item': catalogs[2],
                'plan_date': today,
                'scheduled_start_time': time(11, 0),
                'scheduled_end_time': time(13, 0),
                'planned_duration_minutes': 120,
                'quadrant': 'Q1',
                'order_index': 1,
                'status': 'IN_ACTIVITY'
            },
            {
                'user': users[0],
                'catalog_item': catalogs[6],
                'plan_date': today,
                'scheduled_start_time': time(14, 0),
                'scheduled_end_time': time(15, 0),
                'planned_duration_minutes': 60,
                'quadrant': 'Q2',
                'order_index': 2,
                'status': 'STARTED'
            },
            {
                'user': users[0],
                'catalog_item': catalogs[4],
                'plan_date': today,
                'scheduled_start_time': time(15, 0),
                'scheduled_end_time': time(17, 0),
                'planned_duration_minutes': 120,
                'quadrant': 'Q2',
                'order_index': 3,
                'status': 'PLANNED'
            },
            
            # User 2 plans
            {
                'user': users[1],
                'catalog_item': catalogs[1],
                'plan_date': today,
                'scheduled_start_time': time(9, 0),
                'scheduled_end_time': time(12, 0),
                'planned_duration_minutes': 180,
                'quadrant': 'Q1',
                'order_index': 0,
                'status': 'IN_ACTIVITY'
            },
            {
                'user': users[1],
                'catalog_item': catalogs[5],
                'plan_date': today,
                'scheduled_start_time': time(13, 0),
                'scheduled_end_time': time(15, 0),
                'planned_duration_minutes': 120,
                'quadrant': 'Q2',
                'order_index': 1,
                'status': 'PLANNED'
            },
            {
                'user': users[1],
                'catalog_item': catalogs[8],
                'plan_date': today,
                'scheduled_start_time': time(15, 0),
                'scheduled_end_time': time(16, 0),
                'planned_duration_minutes': 60,
                'quadrant': 'Q3',
                'order_index': 2,
                'status': 'PLANNED'
            },
            
            # User 3 plans
            {
                'user': users[2],
                'catalog_item': catalogs[3],
                'plan_date': today,
                'scheduled_start_time': time(10, 0),
                'scheduled_end_time': time(13, 0),
                'planned_duration_minutes': 180,
                'quadrant': 'Q1',
                'order_index': 0,
                'status': 'COMPLETED'
            },
            {
                'user': users[2],
                'catalog_item': catalogs[7],
                'plan_date': today,
                'scheduled_start_time': time(14, 0),
                'scheduled_end_time': time(14, 30),
                'planned_duration_minutes': 30,
                'quadrant': 'Q2',
                'order_index': 1,
                'status': 'STARTED'
            },
        ]
        
        for data in plans_data:
            TodayPlan.objects.create(**data)
        
        self.stdout.write(self.style.SUCCESS(f'Created {len(plans_data)} today plan items'))

    def create_activity_logs(self):
        """Create activity logs"""
        from decimal import Decimal
        
        today_plans = list(TodayPlan.objects.filter(status__in=['IN_ACTIVITY', 'COMPLETED', 'STARTED']))
        
        for plan in today_plans:
            start_time = timezone.now() - timedelta(hours=random.randint(1, 4))
            
            if plan.status == 'COMPLETED':
                end_time = start_time + timedelta(minutes=plan.planned_duration_minutes)
                status = 'COMPLETED'
                is_completed = True
            elif plan.status == 'IN_ACTIVITY':
                end_time = None
                status = 'IN_PROGRESS'
                is_completed = False
            else:  # STARTED
                end_time = start_time + timedelta(minutes=random.randint(30, 60))
                status = 'STOPPED'
                is_completed = False
            
            activity = ActivityLog.objects.create(
                today_plan=plan,
                user=plan.user,
                actual_start_time=start_time,
                actual_end_time=end_time,
                status=status,
                is_task_completed=is_completed,
                work_notes=f'Worked on {plan.catalog_item.name}'
            )
            
            if end_time:
                activity.calculate_time_worked()
        
        self.stdout.write(self.style.SUCCESS(f'Created activity logs for {len(today_plans)} today plans'))

    def create_pending_tasks(self):
        """Create pending tasks"""
        stopped_activities = ActivityLog.objects.filter(status='STOPPED')
        
        for activity in stopped_activities:
            Pending.objects.create(
                user=activity.user,
                today_plan=activity.today_plan,
                activity_log=activity,
                original_plan_date=activity.today_plan.plan_date,
                minutes_left=activity.today_plan.planned_duration_minutes - activity.minutes_worked,
                reason='Need more time to complete',
                status='PENDING'
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created {stopped_activities.count()} pending tasks'))

    def create_day_sessions(self):
        """Create day sessions"""
        users = list(User.objects.filter(role__in=['EMPLOYEE', 'TEAMLEAD']))
        today = date.today()
        
        for user in users:
            # Today's active session
            DaySession.objects.create(
                user=user,
                session_date=today,
                started_at=timezone.now().replace(hour=9, minute=0, second=0),
                is_active=True
            )
            
            # Yesterday's completed session
            yesterday = today - timedelta(days=1)
            DaySession.objects.create(
                user=user,
                session_date=yesterday,
                started_at=timezone.now().replace(hour=9, minute=0, second=0) - timedelta(days=1),
                ended_at=timezone.now().replace(hour=18, minute=0, second=0) - timedelta(days=1),
                is_active=False
            )
        
        self.stdout.write(self.style.SUCCESS(f'Created day sessions for {len(users)} users'))
