#!/usr/bin/env python
"""
Test script for line chart endpoints
Tests: ProjectCompletionLineChartViewSet and TaskCompletionLineChartViewSet
"""

import os
import sys
import django
from datetime import date, datetime, timedelta
from django.test import TestCase, Client
from django.contrib.auth.models import User as DjangoUser

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
django.setup()

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from schedular.models import User, Projects, Task, Employee, Department

class LineChartEndpointTests:
    """Integration tests for line chart endpoints"""
    
    def __init__(self):
        self.client = APIClient()
        self.test_data = {}
    
    def create_test_users(self):
        """Create test users with different roles"""
        print("\n[*] Creating test users...")
        
        # Admin user
        admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpass123',
            role='ADMIN'
        )
        admin_user.employee_name = 'Admin User'
        admin_user.hrm_department = 'Management'
        admin_user.save()
        print(f"  ✓ Created ADMIN: {admin_user.email}")
        
        # Team Lead user
        team_lead = User.objects.create_user(
            email='teamlead@test.com',
            password='testpass123',
            role='TEAMLEAD'
        )
        team_lead.employee_name = 'Team Lead User'
        team_lead.hrm_department = 'Engineering'
        team_lead.save()
        print(f"  ✓ Created TEAMLEAD: {team_lead.email}")
        
        # Employee user
        employee = User.objects.create_user(
            email='employee@test.com',
            password='testpass123',
            role='EMPLOYEE'
        )
        employee.employee_name = 'Employee User'
        employee.hrm_department = 'Engineering'
        employee.team_lead = team_lead
        employee.save()
        print(f"  ✓ Created EMPLOYEE: {employee.email}")
        
        self.test_data['admin'] = admin_user
        self.test_data['team_lead'] = team_lead
        self.test_data['employee'] = employee
    
    def create_test_projects(self):
        """Create test projects with completion dates"""
        print("\n[*] Creating test projects...")
        today = date.today()
        
        # Create projects with completion dates in different months
        months_back = [
            (today - timedelta(days=60), 'Admin Project 1'),  # ~2 months ago
            (today - timedelta(days=30), 'Employee Project 1'),  # ~1 month ago
            (today - timedelta(days=15), 'Team Project 1'),  # ~15 days ago
            (today, 'Recent Project'),  # Today
        ]
        
        for completed_date, name in months_back:
            project = Projects.objects.create(
                name=name,
                status='COMPLETED',
                handled_by=self.test_data['admin'],
                created_by=self.test_data['admin'],
                start_date=completed_date - timedelta(days=30),
                due_date=completed_date,
                completed_date=completed_date,
                description=f'Test project: {name}',
                working_hours=40,
                duration=30,
            )
            print(f"  ✓ Created project: {name} (completed: {completed_date})")
        
        print(f"  Total projects created: {Projects.objects.count()}")
    
    def create_test_tasks(self):
        """Create test tasks with completion dates"""
        print("\n[*] Creating test tasks...")
        today = date.today()
        
        # Get or create a test project
        project = Projects.objects.first()
        if not project:
            project = Projects.objects.create(
                name='Test Project',
                status='ACTIVE',
                handled_by=self.test_data['admin'],
                created_by=self.test_data['admin'],
                start_date=today - timedelta(days=30),
                due_date=today + timedelta(days=30),
                description='Test project for tasks',
                working_hours=40,
                duration=60,
            )
        
        # Create tasks with completion dates in different months
        months_back = [
            (today - timedelta(days=60), 'Old Task'),  # ~2 months ago
            (today - timedelta(days=30), 'Recent Task 1'),  # ~1 month ago
            (today - timedelta(days=15), 'Recent Task 2'),  # ~15 days ago
            (today - timedelta(days=5), 'Very Recent Task'),  # ~5 days ago
        ]
        
        for completed_date, title in months_back:
            task = Task.objects.create(
                title=title,
                project=project,
                project_lead=self.test_data['admin'],
                status='DONE',
                priority='MEDIUM',
                start_date=completed_date - timedelta(days=7),
                due_date=completed_date,
                completed_at=completed_date,
            )
            print(f"  ✓ Created task: {title} (completed: {completed_date})")
        
        print(f"  Total tasks created: {Task.objects.filter(status='DONE').count()}")
    
    def authenticate_user(self, user):
        """Get auth token for user"""
        refresh = RefreshToken.for_user(user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
        print(f"  ✓ Authenticated as: {user.email} ({user.role})")
    
    def test_project_chart_endpoint(self):
        """Test project completion line chart endpoint"""
        print("\n[*] Testing Project Completion Chart Endpoint")
        print("=" * 50)
        
        # Test 1: Admin access
        print("\n  [Test 1] ADMIN access")
        self.authenticate_user(self.test_data['admin'])
        response = self.client.get('/api/project-completion-chart/')
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Status: {response.status_code}")
            print(f"    - User Role: {data.get('user_role')}")
            print(f"    - Total Completed: {data.get('total_completed')}")
            print(f"    - Data Points: {len(data.get('data', []))}")
            if data.get('data'):
                print(f"    - Sample Data:")
                for item in data['data'][:3]:
                    if item['count'] > 0:
                        print(f"      • {item['month_year']}: {item['count']} projects")
        else:
            print(f"  ✗ Status: {response.status_code}")
            print(f"    Error: {response.json()}")
        
        # Test 2: Employee access
        print("\n  [Test 2] EMPLOYEE access")
        self.authenticate_user(self.test_data['employee'])
        response = self.client.get('/api/project-completion-chart/')
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Status: {response.status_code}")
            print(f"    - User Role: {data.get('user_role')}")
            print(f"    - Department: {data.get('department')}")
        else:
            print(f"  ✗ Status: {response.status_code}")
        
        # Test 3: Query with specific months
        print("\n  [Test 3] Query with months=6")
        self.authenticate_user(self.test_data['admin'])
        response = self.client.get('/api/project-completion-chart/?months=6')
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Status: {response.status_code}")
            print(f"    - Date Range Start: {data['date_range']['start_date']}")
            print(f"    - Date Range End: {data['date_range']['end_date']}")
        else:
            print(f"  ✗ Status: {response.status_code}")
    
    def test_task_chart_endpoint(self):
        """Test task completion line chart endpoint"""
        print("\n[*] Testing Task Completion Chart Endpoint")
        print("=" * 50)
        
        # Test 1: Admin access
        print("\n  [Test 1] Admin access")
        self.authenticate_user(self.test_data['admin'])
        response = self.client.get('/api/task-completion-chart/')
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Status: {response.status_code}")
            print(f"    - User Role: {data.get('user_role')}")
            print(f"    - Total Completed: {data.get('total_completed')}")
            print(f"    - Data Points: {len(data.get('data', []))}")
            if data.get('data'):
                print(f"    - Sample Data:")
                for item in data['data'][:3]:
                    if item['count'] > 0:
                        print(f"      • {item['month_year']}: {item['count']} tasks")
        else:
            print(f"  ✗ Status: {response.status_code}")
            print(f"    Error: {response.json()}")
        
        # Test 2: Employee access
        print("\n  [Test 2] Employee access")
        self.authenticate_user(self.test_data['employee'])
        response = self.client.get('/api/task-completion-chart/')
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Status: {response.status_code}")
            print(f"    - User Role: {data.get('user_role')}")
        else:
            print(f"  ✗ Status: {response.status_code}")
        
        # Test 3: Date range query
        print("\n  [Test 3] Query with date range")
        start_date = (date.today() - timedelta(days=90)).isoformat()
        end_date = date.today().isoformat()
        response = self.client.get(f'/api/task-completion-chart/?start_date={start_date}&end_date={end_date}')
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Status: {response.status_code}")
            print(f"    - Requested Range: {start_date} to {end_date}")
            print(f"    - Returned Data Points: {len(data['data'])}")
        else:
            print(f"  ✗ Status: {response.status_code}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "=" * 60)
        print("LINE CHART ENDPOINTS - INTEGRATION TESTS")
        print("=" * 60)
        
        try:
            self.create_test_users()
            self.create_test_projects()
            self.create_test_tasks()
            self.test_project_chart_endpoint()
            self.test_task_chart_endpoint()
            
            print("\n" + "=" * 60)
            print("✓ All tests completed successfully!")
            print("=" * 60 + "\n")
            
        except Exception as e:
            print(f"\n✗ Error during testing: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    # Clean up old test data
    print("\n[*] Cleaning up old test data...")
    User.objects.filter(email__endswith='@test.com').delete()
    print("  ✓ Cleanup complete")
    
    # Run tests
    tester = LineChartEndpointTests()
    tester.run_all_tests()
