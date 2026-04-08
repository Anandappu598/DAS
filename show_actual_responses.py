"""
Test script to show actual API responses for all 3 endpoints
"""
import os
import sys
import django
from datetime import date, timedelta
import json

# Setup Django
sys.path.insert(0, 'c:/work/das/DAS_Backend/activity')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
django.setup()

from schedular.models import User, TodayPlan, ActivityLog, DailyPlanner
from schedular.serializers_performance import DailyPerformanceSerializer
from django.db.models import Q

print("\n" + "="*100)
print("ACTUAL API RESPONSES - Testing 3 Endpoints")
print("="*100)

# Get first user
user = User.objects.first()
if not user:
    print("❌ No users found")
    sys.exit(1)

print(f"\nTesting with user: {user.email}\n")

# ========================================
# 1. GET /api/daily-performance/ (TODAY)
# ========================================
print("\n" + "="*100)
print("1. GET /api/daily-performance/ → TODAY'S DATA")
print("="*100 + "\n")

today = date.today()
serializer = DailyPerformanceSerializer({
    'user': user,
    'date': today
})

response_today = serializer.data
print("Response:")
print(json.dumps(response_today, indent=2, default=str))

# ========================================
# 2. GET /api/daily-performance/<date>/ (SPECIFIC DATE)
# ========================================
print("\n" + "="*100)
print("2. GET /api/daily-performance/<date>/ → SPECIFIC DATE (2026-04-07)")
print("="*100 + "\n")

specific_date = date(2026, 4, 7)
serializer = DailyPerformanceSerializer({
    'user': user,
    'date': specific_date
})

response_date = serializer.data
print("Response:")
print(json.dumps(response_date, indent=2, default=str))

# ========================================
# 3. GET /api/daily-performance/range/<start>/<end>/ (DATE RANGE)
# ========================================
print("\n" + "="*100)
print("3. GET /api/daily-performance/range/2026-04-05/2026-04-09/ → DATE RANGE")
print("="*100 + "\n")

start_date = date(2026, 4, 5)
end_date = date(2026, 4, 9)

# Generate responses for each day in range
date_range_responses = []
current_date = start_date
while current_date <= end_date:
    serializer = DailyPerformanceSerializer({
        'user': user,
        'date': current_date
    })
    date_range_responses.append(serializer.data)
    current_date += timedelta(days=1)

response_range = {
    "start_date": str(start_date),
    "end_date": str(end_date),
    "days_count": len(date_range_responses),
    "daily_data": date_range_responses
}

print("Response:")
print(json.dumps(response_range, indent=2, default=str))

# ========================================
# SUMMARY
# ========================================
print("\n" + "="*100)
print("SUMMARY")
print("="*100)
print(f"""
✓ Today's Data (GET /api/daily-performance/)
  - Date: {today}
  - Planned tasks: {response_today['planned_summary']['total_tasks']}
  - Hours worked: {response_today['actual_summary']['total_hours_worked']}

✓ Specific Date (GET /api/daily-performance/2026-04-07/)
  - Date: {specific_date}
  - Daily plan hours: {response_date['planned_summary']['daily_plan']['planned_hours']}
  - Has daily planner: {response_date['planned_summary']['daily_plan']['has_daily_planner']}
  - Planned tasks: {response_date['planned_summary']['planned_tasks']['count']}
  - Unplanned tasks: {response_date['planned_summary']['unplanned_tasks']['count']}

✓ Date Range (GET /api/daily-performance/range/2026-04-05/2026-04-09/)
  - Start: {start_date}
  - End: {end_date}
  - Days: {len(date_range_responses)}
  - Data included for each day
""")

print("="*100)
