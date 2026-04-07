#!/usr/bin/env python
"""
Comprehensive test to verify ALL user roles get consistent data
between "my projects" API and line chart
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

def get_my_projects_api_count(user):
    """Simulate the "my projects" API filtering (with filter=my)"""
    queryset = Projects.objects.filter(
        status='COMPLETED',
        completed_date__isnull=False,
        completed_date__gte=date.today() - timedelta(days=365),
        completed_date__lte=date.today()
    )
    
    queryset = queryset.filter(
        Q(created_by=user) |
        Q(assignees=user) |
        Q(project_lead=user) |
        Q(handled_by=user) |
        Q(tasks__assignees__user=user)
    ).distinct()
    
    return queryset.count(), queryset

def get_line_chart_count(user, role):
    """Simulate the line chart filtering"""
    today = date.today()
    start_date = today - timedelta(days=365)
    end_date = today
    
    queryset = Projects.objects.filter(
        status='COMPLETED',
        completed_date__isnull=False,
        completed_date__gte=start_date,
        completed_date__lte=end_date
    )
    
    # Apply the line chart filtering logic
    if role == 'ADMIN':
        pass  # Admin sees all
    elif role == 'MANAGER':
        subordinates = user.get_all_subordinates()
        queryset = queryset.filter(
            Q(project_lead=user) |
            Q(handled_by=user) |
            Q(created_by=user) |
            Q(project_lead__in=subordinates) |
            Q(handled_by__in=subordinates) |
            Q(created_by__in=subordinates)
        ).distinct()
    elif role == 'TEAMLEAD':
        team_members = user.get_team_members()
        queryset = queryset.filter(
            Q(project_lead=user) |
            Q(handled_by=user) |
            Q(created_by=user) |
            Q(project_lead__in=team_members) |
            Q(handled_by__in=team_members) |
            Q(created_by__in=team_members)
        ).distinct()
    else:  # EMPLOYEE
        queryset = queryset.filter(
            Q(project_lead=user) |
            Q(handled_by=user) |
            Q(created_by=user) |
            Q(assignees=user) |
            Q(tasks__assignees__user=user)
        ).distinct()
    
    return queryset.count(), queryset

def main():
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST: MY PROJECTS API vs LINE CHART FOR ALL USERS")
    print("="*80)
    
    # Get all active users
    users = User.objects.filter(is_active=True)
    
    print(f"\nTesting {users.count()} users...\n")
    
    results = []
    
    for user in users:
        api_count, api_qs = get_my_projects_api_count(user)
        chart_count, chart_qs = get_line_chart_count(user, user.role)
        
        match = "✓" if api_count == chart_count else "✗"
        
        results.append({
            'user': user.email,
            'role': user.role,
            'api_count': api_count,
            'chart_count': chart_count,
            'match': match
        })
        
        print(f"{match} {user.email} ({user.role})")
        print(f"   My Projects API: {api_count}")
        print(f"   Line Chart: {chart_count}")
        
        if api_count != chart_count:
            print(f"   MISMATCH: Difference = {abs(api_count - chart_count)}")
            
            # Show the projects that are different
            api_ids = set(api_qs.values_list('id', flat=True))
            chart_ids = set(chart_qs.values_list('id', flat=True))
            
            missing_in_chart = api_ids - chart_ids
            extra_in_chart = chart_ids - api_ids
            
            if missing_in_chart:
                print(f"   Missing in line chart:")
                for proj in api_qs.filter(id__in=missing_in_chart):
                    print(f"     - {proj.name}")
            
            if extra_in_chart:
                print(f"   Extra in line chart:")
                for proj in chart_qs.filter(id__in=extra_in_chart):
                    print(f"     - {proj.name}")
        else:
            if api_count > 0:
                print(f"   ✓ Both showing {api_count} projects")
        
        print()
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    total_users = len(results)
    matching = sum(1 for r in results if r['match'] == '✓')
    mismatching = sum(1 for r in results if r['match'] == '✗')
    
    print(f"Total users tested: {total_users}")
    print(f"Matching results: {matching}")
    print(f"Mismatching results: {mismatching}")
    
    if mismatching == 0:
        print("\n✅ ALL USERS show consistent data between API and line chart!")
    else:
        print(f"\n⚠️ {mismatching} users have mismatched data")
        print("\nUsers with mismatches:")
        for r in results:
            if r['match'] == '✗':
                print(f"  - {r['user']} ({r['role']}): API={r['api_count']}, Chart={r['chart_count']}")
    
    print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
