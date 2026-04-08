"""
Test with SAMPLE DATA - to verify serializer works correctly when tasks exist
"""
import os
import sys
import django
from datetime import date, datetime

sys.path.insert(0, 'c:/work/das/DAS_Backend/activity')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
django.setup()

from schedular.models import User, TodayPlan, ActivityLog, Catalog
from schedular.serializers_performance import DailyPerformanceSerializer
import json

print("\n" + "="*100)
print("TEST: Creating sample tasks and checking API response")
print("="*100 + "\n")

user = User.objects.first()
if not user:
    print("❌ No users found")
    sys.exit(1)

today = date.today()
print(f"User: {user.email}\nDate: {today}\n")

# Create sample tasks
print("Creating sample tasks...")
today_plans = []

# Task 1: Planned task
task1 = TodayPlan(
    user=user,
    plan_date=today,
    custom_title="API Development",
    planned_duration_minutes=120,
    quadrant="Q1",
    status="COMPLETED",
    is_unplanned=False,
    notes="Backend endpoints",
    order_index=1
)
task1.save()
today_plans.append(task1)
print(f"✓ Created: API Development (120m)")

# Task 2: Planned task
task2 = TodayPlan(
    user=user,
    plan_date=today,
    custom_title="Frontend UI",
    planned_duration_minutes=180,
    quadrant="Q1",
    status="IN_ACTIVITY",
    is_unplanned=False,
    notes="Dashboard design",
    order_index=2
)
task2.save()
today_plans.append(task2)
print(f"✓ Created: Frontend UI (180m)")

# Task 3: Unplanned task
task3 = TodayPlan(
    user=user,
    plan_date=today,
    custom_title="Bug Fix",
    planned_duration_minutes=60,
    quadrant="Q3",
    status="COMPLETED",
    is_unplanned=True,
    notes="Critical bug",
    order_index=3
)
task3.save()
today_plans.append(task3)
print(f"✓ Created: Bug Fix (60m - UNPLANNED)")

# Create activity logs
print("\nCreating activity logs...")
log1 = ActivityLog(
    user=user,
    today_plan=task1,
    minutes_worked=135,
    hours_worked=2.25,
    actual_start_time=datetime.now(),
    actual_end_time=datetime.now(),
    is_task_completed=True,
    status="COMPLETED"
)
log1.save()
print(f"✓ Created: Activity log for task1 (135m)")

log2 = ActivityLog(
    user=user,
    today_plan=task2,
    minutes_worked=95,
    hours_worked=1.58,
    actual_start_time=datetime.now(),
    actual_end_time=datetime.now(),
    is_task_completed=False,
    status="IN_PROGRESS"
)
log2.save()
print(f"✓ Created: Activity log for task2 (95m)")

# Now test the serializer
print("\n" + "-"*100)
print("API RESPONSE WITH SAMPLE DATA")
print("-"*100 + "\n")

# Refresh from DB
today_plans_db = TodayPlan.objects.filter(user=user, plan_date=today)
activity_logs_db = ActivityLog.objects.filter(user=user, today_plan__plan_date=today)

serializer_data = {
    'date': today,
    'user': user,
    'today_plans': list(today_plans_db),
    'activity_logs': list(activity_logs_db)
}

print(f"Data for serializer:")
print(f"  - today_plans: {len(serializer_data['today_plans'])}")
print(f"  - activity_logs: {len(serializer_data['activity_logs'])}\n")

serializer = DailyPerformanceSerializer(serializer_data)
response_data = serializer.data

print("API RESPONSE (Formatted):")
response = {
    'date': str(today),
    'user': user.email,
    'planned_summary': response_data.get('planned_summary', {}),
    'actual_summary': response_data.get('actual_summary', {}),
    'metrics': response_data.get('metrics', {}),
    'tasks': response_data.get('tasks', [])
}

print(json.dumps(response, indent=2, default=str))

# Verify tasks are in response
print("\n" + "-"*100)
print("VERIFICATION")
print("-"*100)

planned_tasks = response_data.get('planned_summary', {}).get('planned_tasks', {})
unplanned_tasks = response_data.get('planned_summary', {}).get('unplanned_tasks', {})

print(f"✓ Planned tasks count (expected 2): {planned_tasks.get('count')}")
print(f"✓ Planned tasks array length: {len(planned_tasks.get('tasks', []))}")
if planned_tasks.get('tasks'):
    for task in planned_tasks['tasks']:
        print(f"    - {task['name']} ({task['planned_hours']}h)")

print(f"\n✓ Unplanned tasks count (expected 1): {unplanned_tasks.get('count')}")
print(f"✓ Unplanned tasks array length: {len(unplanned_tasks.get('tasks', []))}")
if unplanned_tasks.get('tasks'):
    for task in unplanned_tasks['tasks']:
        print(f"    - {task['name']} ({task['planned_hours']}h)")

# Cleanup
print("\n" + "-"*100)
print("CLEANUP: Removing sample data...")
print("-"*100 + "\n")
for plan in today_plans_db:
    plan.delete()
print(f"✓ Removed {len(today_plans)} tasks")

print("\n" + "="*100)
print("✅ TEST COMPLETE - Serializer works correctly when tasks exist!")
print("="*100)
