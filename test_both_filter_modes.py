#!/usr/bin/env python
"""
Test to verify myprojects API vs line chart with BOTH filter modes
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
sys.path.insert(0, '/work/DAS_BACKEND/activity')

django.setup()

from datetime import date, timedelta
from django.db.models import Q
from schedular.models import User, Projects

def test_user(user, test_with_my_filter=False):
    """Test a single user"""
    today = date.today()
    start_date = today - timedelta(days=365)
    end_date = today
    
    # Base queryset
    base_qs = Projects.objects.filter(
        status='COMPLETED',
        completed_date__isnull=False,
        completed_date__gte=start_date,
        completed_date__lte=end_date
    )
    
    # ===== MY PROJECTS API LOGIC =====
    # From ProjectViewSet.get_queryset() -> ProjectQuerySetMixin.get_queryset()
    
    if test_with_my_filter:
        # WITH filter='my': Applies 'my' filter regardless of role
        api_qs = base_qs.filter(
            Q(created_by=user) |
            Q(assignees=user) |
            Q(project_lead=user) |
            Q(handled_by=user) |
            Q(tasks__assignees__user=user)
        ).distinct()
        api_label = "API (filter=my)"
    else:
        # WITHOUT filter='my': Applies role-based filtering
        if user.role == 'ADMIN':
            api_qs = base_qs  # ADMIN sees all
            api_label = "API (default/ADMIN)"
        elif user.role == 'MANAGER':
            subordinates = user.get_all_subordinates()
            api_qs = base_qs.filter(
                Q(project_lead=user) |
                Q(handled_by=user) |
                Q(created_by=user) |
                Q(project_lead__in=subordinates) |
                Q(handled_by__in=subordinates) |
                Q(created_by__in=subordinates)
            ).distinct()
            api_label = "API (default/MANAGER)"
        elif user.role == 'TEAMLEAD':
            team_members = user.get_team_members()
            api_qs = base_qs.filter(
                Q(project_lead=user) |
                Q(handled_by=user) |
                Q(created_by=user) |
                Q(project_lead__in=team_members) |
                Q(handled_by__in=team_members) |
                Q(created_by__in=team_members)
            ).distinct()
            api_label = "API (default/TEAMLEAD)"
        else:  # EMPLOYEE
            api_qs = base_qs.filter(
                Q(project_lead=user) |
                Q(handled_by=user) |
                Q(created_by=user) |
                Q(assignees=user) |
                Q(tasks__assignees__user=user)
            ).distinct()
            api_label = "API (default/EMPLOYEE)"
    
    # ===== LINE CHART LOGIC =====
    # From ProjectCompletionLineChartViewSet.list()
    
    line_chart_qs = Projects.objects.filter(
        status='COMPLETED',
        completed_date__isnull=False,
        completed_date__gte=start_date,
        completed_date__lte=end_date
    )
    
    if test_with_my_filter:
        # WITH filter='my': Always applies user-specific filters
        line_chart_qs = line_chart_qs.filter(
            Q(created_by=user) |
            Q(assignees=user) |
            Q(project_lead=user) |
            Q(handled_by=user) |
            Q(tasks__assignees__user=user)
        ).distinct()
        chart_label = "Chart (filter=my)"
    else:
        # WITHOUT filter='my': Applies role-based filtering
        if user.role == 'ADMIN':
            line_chart_qs = line_chart_qs  # ADMIN sees all
            chart_label = "Chart (default/ADMIN)"
        elif user.role == 'MANAGER':
            subordinates = user.get_all_subordinates()
            line_chart_qs = line_chart_qs.filter(
                Q(project_lead=user) |
                Q(handled_by=user) |
                Q(created_by=user) |
                Q(project_lead__in=subordinates) |
                Q(handled_by__in=subordinates) |
                Q(created_by__in=subordinates)
            ).distinct()
            chart_label = "Chart (default/MANAGER)"
        elif user.role == 'TEAMLEAD':
            team_members = user.get_team_members()
            line_chart_qs = line_chart_qs.filter(
                Q(project_lead=user) |
                Q(handled_by=user) |
                Q(created_by=user) |
                Q(project_lead__in=team_members) |
                Q(handled_by__in=team_members) |
                Q(created_by__in=team_members)
            ).distinct()
            chart_label = "Chart (default/TEAMLEAD)"
        else:  # EMPLOYEE
            line_chart_qs = line_chart_qs.filter(
                Q(project_lead=user) |
                Q(handled_by=user) |
                Q(created_by=user) |
                Q(assignees=user) |
                Q(tasks__assignees__user=user)
            ).distinct()
            chart_label = "Chart (default/EMPLOYEE)"
    
    api_count = api_qs.count()
    chart_count = line_chart_qs.count()
    match = api_count == chart_count
    
    return {
        'match': match,
        'api_label': api_label,
        'api_count': api_count,
        'chart_label': chart_label,
        'chart_count': chart_count,
        'api_qs': api_qs,
        'chart_qs': line_chart_qs,
    }

def main():
    print("\n" + "="*90)
    print("COMPLETE TEST: API vs LINE CHART WITH BOTH FILTER MODES")
    print("="*90)
    
    # Get admin users to test
    admin_users = User.objects.filter(role='ADMIN', is_active=True)
    employee_users = User.objects.filter(role='EMPLOYEE', is_active=True)[:2]
    
    print("\n" + "-"*90)
    print("TEST 1: ADMIN USERS")
    print("-"*90)
    
    for user in admin_users:
        print(f"\nUser: {user.email}")
        
        # Test without filter
        result = test_user(user, test_with_my_filter=False)
        print(f"  {result['api_label']}: {result['api_count']}")
        print(f"  {result['chart_label']}: {result['chart_count']}")
        if not result['match']:
            print(f"  ✗ MISMATCH")
        else:
            print(f"  ✓ Match")
        
        # Test with my filter
        result_my = test_user(user, test_with_my_filter=True)
        print(f"  {result_my['api_label']}: {result_my['api_count']}")
        print(f"  {result_my['chart_label']}: {result_my['chart_count']}")
        if not result_my['match']:
            print(f"  ✗ MISMATCH")
        else:
            print(f"  ✓ Match")
    
    print("\n" + "-"*90)
    print("TEST 2: EMPLOYEE USERS")
    print("-"*90)
    
    for user in employee_users:
        if not user:
            continue
        print(f"\nUser: {user.email}")
        
        # Test without filter
        result = test_user(user, test_with_my_filter=False)
        print(f"  {result['api_label']}: {result['api_count']}")
        print(f"  {result['chart_label']}: {result['chart_count']}")
        if not result['match']:
            print(f"  ✗ MISMATCH")
        else:
            print(f"  ✓ Match")
        
        # Test with my filter
        result_my = test_user(user, test_with_my_filter=True)
        print(f"  {result_my['api_label']}: {result_my['api_count']}")
        print(f"  {result_my['chart_label']}: {result_my['chart_count']}")
        if not result_my['match']:
            print(f"  ✗ MISMATCH")
        else:
            print(f"  ✓ Match")
    
    print("\n" + "="*90 + "\n")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
