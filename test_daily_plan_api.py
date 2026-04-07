"""
Test script to verify Daily Plan API includes daily_plan data
"""
import os
import sys
import django
from datetime import date

# Setup Django
sys.path.insert(0, 'c:/work/das/DAS_Backend/activity')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
django.setup()

from schedular.models import User, TodayPlan, ActivityLog, DailyPlanner
from schedular.serializers_performance import DailyPerformanceSerializer
import json

print("\n" + "="*80)
print("TESTING DAILY PLAN API - Checking if daily_plan data is included")
print("="*80 + "\n")

# Get all users and their data
users = User.objects.all()[:1]  # Get first user

if not users:
    print("❌ No users found in database")
    sys.exit(1)

user = users[0]
print(f"Testing with user: {user.email}")
print(f"User name: {user.employee_name or 'N/A'}")

# Check data for today
today = date.today()
print(f"\nChecking data for: {today}")

# Check DailyPlanner data
daily_planner = DailyPlanner.objects.filter(user=user, date=today).first()
if daily_planner:
    print(f"✓ Daily Planner found:")
    print(f"  - Planned hours: {daily_planner.planned_hours}")
    print(f"  - Tasks: {daily_planner.tasks}")
else:
    print(f"✗ No Daily Planner entry for {today}")

# Check TodayPlan data
today_plans = TodayPlan.objects.filter(user=user, plan_date=today)
print(f"\n✓ Found {today_plans.count()} TodayPlan entries")
for plan in today_plans:
    print(f"  - {plan.custom_title}: {plan.planned_duration_minutes}m (status: {plan.status})")

# Check ActivityLog data - skip for now, just test serializer
print(f"\n(Skipping ActivityLog check - focus on serializer test)")

# Now test the serializer
print("\n" + "-"*80)
print("SERIALIZER OUTPUT TEST")
print("-"*80 + "\n")

try:
    serializer = DailyPerformanceSerializer({
        'user': user,
        'date': today
    })
    
    data = serializer.data
    print("✓ Serializer executed successfully")
    
    # Check if daily_plan section exists
    if 'planned' in data and 'daily_plan' in data['planned']:
        print("\n✓✓✓ DAILY PLAN SECTION FOUND IN RESPONSE! ✓✓✓")
        daily_plan_data = data['planned']['daily_plan']
        print(f"\nDaily Plan Data:")
        print(f"  - Date: {daily_plan_data.get('date')}")
        print(f"  - Planned Hours: {daily_plan_data.get('planned_hours')}")
        print(f"  - Has Daily Planner: {daily_plan_data.get('has_daily_planner')}")
        
        # Pretty print the planned section
        print(f"\nFull Planned Section:")
        print(json.dumps(data['planned'], indent=2))
        
    else:
        print("\n✗ Daily plan section NOT found in response")
        print("\nResponse structure:")
        print(json.dumps(data, indent=2)[:500])
        
except Exception as e:
    print(f"\n❌ Error running serializer: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80)
