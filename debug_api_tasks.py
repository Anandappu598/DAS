"""
Debug script to test API and see why tasks aren't showing
"""
import os
import sys
import django
from datetime import date

sys.path.insert(0, 'c:/work/das/DAS_Backend/activity')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
django.setup()

from schedular.models import User, TodayPlan, ActivityLog
from schedular.serializers_performance import DailyPerformanceSerializer
import json

print("\n" + "="*100)
print("DEBUG: API RESPONSE WITH TASKS")
print("="*100 + "\n")

user = User.objects.first()
if not user:
    print("❌ No users found")
    sys.exit(1)

# Check raw database
today = date.today()
print(f"User: {user.email}")
print(f"Date: {today}\n")

# Check what's in database
today_plans = TodayPlan.objects.filter(user=user, plan_date=today)
print(f"📊 TodayPlan Records in Database:")
print(f"   Count: {today_plans.count()}")
if today_plans.count() > 0:
    for plan in today_plans[:5]:  # Show first 5
        task_name = plan.catalog_item.name if plan.catalog_item else plan.custom_title
        print(f"   - ID:{plan.id} | {task_name} | {plan.planned_duration_minutes}m | Unplanned:{plan.is_unplanned}")
else:
    print("   (No tasks found for this date)")

# Check ActivityLogs
activity_logs = ActivityLog.objects.filter(user=user, today_plan__plan_date=today)
print(f"\n📊 ActivityLog Records in Database:")
print(f"   Count: {activity_logs.count()}")
if activity_logs.count() > 0:
    for log in activity_logs[:5]:
        print(f"   - ID:{log.id} | Task:{log.today_plan.id} | {log.minutes_worked}m")
else:
    print("   (No activity logs)")

# Now test the serializer
print("\n" + "-"*100)
print("SERIALIZER TEST")
print("-"*100 + "\n")

serializer_data = {
    'date': today,
    'user': user,
    'today_plans': list(today_plans),
    'activity_logs': list(activity_logs)
}

print(f"Data passed to serializer:")
print(f"  - date: {serializer_data['date']}")
print(f"  - user: {serializer_data['user'].email}")
print(f"  - today_plans count: {len(serializer_data['today_plans'])}")
print(f"  - activity_logs count: {len(serializer_data['activity_logs'])}")

serializer = DailyPerformanceSerializer(serializer_data)
response_data = serializer.data

print(f"\n✓ Serializer executed successfully\n")

# Show the response
print("API RESPONSE:")
print(json.dumps({
    'date': str(today),
    'user': user.email,
    'planned_summary': response_data.get('planned_summary', {}),
    'actual_summary': response_data.get('actual_summary', {}),
    'metrics': response_data.get('metrics', {}),
    'tasks': response_data.get('tasks', [])
}, indent=2, default=str))

# Check if tasks are in the response
planned_tasks = response_data.get('planned_summary', {}).get('planned_tasks', {}).get('tasks', [])
unplanned_tasks = response_data.get('planned_summary', {}).get('unplanned_tasks', {}).get('tasks', [])

print(f"\n" + "-"*100)
print("TASK BREAKDOWN:")
print("-"*100)
print(f"Planned Tasks in Response: {len(planned_tasks)}")
if planned_tasks:
    for task in planned_tasks:
        print(f"  - {task}")
print(f"\nUnplanned Tasks in Response: {len(unplanned_tasks)}")
if unplanned_tasks:
    for task in unplanned_tasks:
        print(f"  - {task}")

print("\n" + "="*100)
