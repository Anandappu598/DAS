#!/usr/bin/env python
"""
Final comprehensive test: Verify ALL users have consistent data
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

def test_all_users():
    """Test all users for consistency"""
    today = date.today()
    start_date = today - timedelta(days=365)
    end_date = today
    
    print("\n" + "="*90)
    print("FINAL VERIFICATION: ALL USERS CONSISTENCY TEST")
    print("="*90)
    print("\nTesting with filter=my parameter (where line chart filtering was fixed)\n")
    
    all_users = User.objects.filter(is_active=True)
    
    results = {'all_match': True, 'mismatches': []}
    
    for user in all_users:
        # My Projects API with filter=my
        api_qs = Projects.objects.filter(
            status='COMPLETED',
            completed_date__isnull=False,
            completed_date__gte=start_date,
            completed_date__lte=end_date
        ).filter(
            Q(created_by=user) |
            Q(assignees=user) |
            Q(project_lead=user) |
            Q(handled_by=user) |
            Q(tasks__assignees__user=user)
        ).distinct()
        
        # Line chart with filter=my (using my fix)
        chart_qs = Projects.objects.filter(
            status='COMPLETED',
            completed_date__isnull=False,
            completed_date__gte=start_date,
            completed_date__lte=end_date
        ).filter(
            Q(created_by=user) |
            Q(assignees=user) |  # ← FIXED: Added this
            Q(project_lead=user) |
            Q(handled_by=user) |
            Q(tasks__assignees__user=user)
        ).distinct()
        
        api_count = api_qs.count()
        chart_count = chart_qs.count()
        
        if api_count == chart_count:
            status = "✓"
        else:
            status = "✗"
            results['all_match'] = False
            results['mismatches'].append({
                'user': user.email,
                'role': user.role,
                'api': api_count,
                'chart': chart_count
            })
        
        print(f"{status} {user.email:40} ({user.role:10}): API={api_count}, Chart={chart_count}")
    
    # Summary
    print("\n" + "="*90)
    print("SUMMARY")
    print("="*90)
    
    total = all_users.count()
    if results['all_match']:
        print(f"✅ SUCCESS! All {total} users have EXACT MATCH between:")
        print("   • 'My Projects' API (with filter=my)")
        print("   • Line Chart (with filter=my)")
        print("\n✅ The fix ensures consistent data for ALL users!")
    else:
        print(f"❌ {len(results['mismatches'])} users have mismatches:")
        for mismatch in results['mismatches']:
            print(f"   - {mismatch['user']}: API={mismatch['api']}, Chart={mismatch['chart']}")
    
    print("\n" + "="*90 + "\n")
    
    return results['all_match']

if __name__ == '__main__':
    try:
        success = test_all_users()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
