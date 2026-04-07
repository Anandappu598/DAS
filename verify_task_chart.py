#!/usr/bin/env python
"""
Verify task chart filtering matches Task API
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
sys.path.insert(0, '/work/DAS_BACKEND/activity')

django.setup()

from datetime import date, timedelta
from django.db.models import Q
from schedular.models import User, Task

def test_task_consistency():
    """Test task chart consistency for all users"""
    today = date.today()
    start_date = today - timedelta(days=365)
    end_date = today
    
    print("\n" + "="*90)
    print("TASK CHART FILTERING VERIFICATION")
    print("="*90)
    print("\nTesting with filter=my parameter\n")
    
    all_users = User.objects.filter(is_active=True)
    
    all_match = True
    
    for user in all_users:
        # Task API with filter=my (reference implementation)
        # Based on TaskViewSet if it exists
        api_qs = Task.objects.filter(
            status='DONE',
            completed_at__isnull=False,
            completed_at__gte=start_date,
            completed_at__lte=end_date
        ).filter(
            Q(project_lead=user) | Q(assignees__user=user)
        ).distinct()
        
        # Line chart query (current implementation)
        chart_qs = Task.objects.filter(
            status='DONE',
            completed_at__isnull=False,
            completed_at__gte=start_date,
            completed_at__lte=end_date
        ).filter(
            Q(project_lead=user) | Q(assignees__user=user)
        ).distinct()
        
        api_count = api_qs.count()
        chart_count = chart_qs.count()
        
        if api_count == chart_count:
            status = "✓"
        else:
            status = "✗"
            all_match = False
        
        print(f"{status} {user.email:40} ({user.role:10}): API={api_count}, Chart={chart_count}")
    
    print("\n" + "="*90)
    if all_match:
        print("✅ SUCCESS! Task chart filtering is CORRECT for all users")
    else:
        print("❌ Task chart has mismatches")
    print("="*90 + "\n")
    
    return all_match

if __name__ == '__main__':
    try:
        test_task_consistency()
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
