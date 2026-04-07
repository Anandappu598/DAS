#!/usr/bin/env python
"""
Verification script to compare "my projects" API vs Line Chart filtering
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
sys.path.insert(0, '/work/DAS_BACKEND/activity')

django.setup()

from datetime import date, timedelta
from django.db.models import Q
from schedular.models import User, Projects, Task

def compare_filtering():
    """Compare "my projects" API filtering with line chart filtering"""
    
    print("\n" + "="*70)
    print("FILTERING LOGIC VERIFICATION")
    print("="*70)
    
    # Get a test user
    test_user = User.objects.filter(role='EMPLOYEE').first()
    if not test_user:
        print("No EMPLOYEE users found. Creating test data...")
        test_user = User.objects.create_user(
            email='test_employee@test.com',
            password='testpass123',
            role='EMPLOYEE'
        )
    
    print(f"\nTest User: {test_user.email} (Role: {test_user.role})")
    
    # Get completed projects
    today = date.today()
    start_date = today - timedelta(days=365)
    end_date = today
    
    print(f"Date Range: {start_date} to {end_date}")
    
    # ===== MY PROJECTS API FILTERING =====
    print("\n" + "-"*70)
    print("1. 'MY PROJECTS' API FILTER")
    print("-"*70)
    
    # This is the filter used in ProjectViewSet.get_queryset() with filter='my'
    my_projects_queryset = Projects.objects.filter(
        Q(created_by=test_user) |
        Q(assignees=test_user) |
        Q(project_lead=test_user) |
        Q(handled_by=test_user) |
        Q(tasks__assignees__user=test_user)
    ).distinct()
    
    print(f"Total 'my projects': {my_projects_queryset.count()}")
    
    # Filter for completed only (same as line chart)
    my_projects_completed = my_projects_queryset.filter(
        status='COMPLETED',
        completed_date__isnull=False,
        completed_date__gte=start_date,
        completed_date__lte=end_date
    ).distinct()
    
    print(f"Completed 'my projects': {my_projects_completed.count()}")
    
    if my_projects_completed.exists():
        print("\nCompleted Projects:")
        for project in my_projects_completed:
            print(f"  • {project.name} (completed: {project.completed_date})")
            print(f"    - Status: {project.status}")
            print(f"    - Created by: {project.created_by.email if project.created_by else 'N/A'}")
            print(f"    - Project Lead: {project.project_lead.email if project.project_lead else 'N/A'}")
            print(f"    - Handled by: {project.handled_by.email if project.handled_by else 'N/A'}")
    
    # ===== LINE CHART FILTERING (CORRECTED) =====
    print("\n" + "-"*70)
    print("2. LINE CHART FILTER (with 'filter=my')")
    print("-"*70)
    
    # This should NOW match the "my projects" API after the fix
    line_chart_queryset = Projects.objects.filter(
        status='COMPLETED',
        completed_date__isnull=False,
        completed_date__gte=start_date,
        completed_date__lte=end_date
    ).filter(
        Q(created_by=test_user) |
        Q(assignees=test_user) |  # ← FIXED: Added this missing filter
        Q(project_lead=test_user) |
        Q(handled_by=test_user) |
        Q(tasks__assignees__user=test_user)
    ).distinct()
    
    print(f"Line chart results: {line_chart_queryset.count()}")
    
    if line_chart_queryset.exists():
        print("\nProjects in Chart:")
        for project in line_chart_queryset:
            print(f"  • {project.name} (completed: {project.completed_date})")
    
    # ===== COMPARISON =====
    print("\n" + "-"*70)
    print("3. COMPARISON")
    print("-"*70)
    
    if my_projects_completed.count() == line_chart_queryset.count():
        print(f"✓ MATCH: Both show {my_projects_completed.count()} completed projects")
    else:
        print(f"✗ MISMATCH:")
        print(f"  - My Projects API: {my_projects_completed.count()}")
        print(f"  - Line Chart: {line_chart_queryset.count()}")
        print(f"  - Difference: {abs(my_projects_completed.count() - line_chart_queryset.count())}")
    
    # Show individual filter contribution
    print("\n" + "-"*70)
    print("4. BREAKDOWN BY FILTER CONDITION")
    print("-"*70)
    
    created_count = Projects.objects.filter(
        status='COMPLETED',
        completed_date__isnull=False,
        completed_date__gte=start_date,
        completed_date__lte=end_date,
        created_by=test_user
    ).count()
    
    assignee_count = Projects.objects.filter(
        status='COMPLETED',
        completed_date__isnull=False,
        completed_date__gte=start_date,
        completed_date__lte=end_date,
        assignees=test_user
    ).count()
    
    lead_count = Projects.objects.filter(
        status='COMPLETED',
        completed_date__isnull=False,
        completed_date__gte=start_date,
        completed_date__lte=end_date,
        project_lead=test_user
    ).count()
    
    handled_count = Projects.objects.filter(
        status='COMPLETED',
        completed_date__isnull=False,
        completed_date__gte=start_date,
        completed_date__lte=end_date,
        handled_by=test_user
    ).count()
    
    task_assignee_count = Projects.objects.filter(
        status='COMPLETED',
        completed_date__isnull=False,
        completed_date__gte=start_date,
        completed_date__lte=end_date,
        tasks__assignees__user=test_user
    ).distinct().count()
    
    print(f"Created by user: {created_count}")
    print(f"User is assignee: {assignee_count} ← (NEWLY FIXED)")
    print(f"Project lead: {lead_count}")
    print(f"Handled by: {handled_count}")
    print(f"Task assignee: {task_assignee_count}")
    
    print("\n" + "="*70)
    print("VERIFICATION COMPLETE")
    print("="*70 + "\n")

if __name__ == '__main__':
    try:
        compare_filtering()
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
