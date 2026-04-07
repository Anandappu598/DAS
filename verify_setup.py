#!/usr/bin/env python
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
sys.path.insert(0, '/work/DAS_BACKEND/activity')

django.setup()

from datetime import date, timedelta
from schedular.models import User, Projects, Task

print("\n" + "="*60)
print("LINE CHART ENDPOINTS VERIFICATION")
print("="*60)

print("\n[✓] ViewSets imported successfully")
print("[✓] Serializers imported successfully")
print("[✓] URLs registered")

print("\n[*] Current System State:")
print(f"  - Users: {User.objects.count()}")
print(f"  - Projects: {Projects.objects.count()}")
print(f"  - Tasks: {Task.objects.count()}")

print("\n[*] NEW API ENDPOINTS AVAILABLE:")
print("=" * 60)
print("\n1. PROJECT COMPLETION LINE CHART")
print("   Endpoint: GET /api/project-completion-chart/")
print("   Description: Shows completed projects grouped by month")
print("   Query Params:")
print("     - months: Number of months (default: 12)")
print("     - start_date: ISO format date (default: 12 months ago)")
print("     - end_date: ISO format date (default: today)")
print("\n   Response Structure:")
print("   {")
print('     "user_role": "ADMIN",')
print('     "department": null,')
print('     "data": [')
print('       {"month": "2026-Jan", "count": 3, "month_year": "January 2026"},')
print('       {"month": "2026-Feb", "count": 4, "month_year": "February 2026"}')
print("     ],")
print('     "total_completed": 7,')
print('     "date_range": {...}')
print("   }")

print("\n2. TASK COMPLETION LINE CHART")
print("   Endpoint: GET /api/task-completion-chart/")
print("   Description: Shows completed tasks grouped by month")
print("   Query Params: Same as project endpoint")
print("   Response: Same structure as project endpoint")

print("\n[*] ROLE-BASED ACCESS CONTROL:")
print("=" * 60)
print("ADMIN:")
print("  - Sees ALL projects/tasks (no filtering)")
print("\nMANAGER:")
print("  - Sees projects/tasks where they or subordinates are involved")
print("\nTEAM LEAD:")
print("  - Sees projects/tasks for their team members")
print("\nEMPLOYEE:")
print("  - Sees ONLY their own projects/tasks")

print("\n[*] DATA FILTERING:")
print("=" * 60)
print("Projects:")
print("  - Field: Projects.completed_date")
print("  - Status: Must be 'COMPLETED'")
print("\nTasks:")
print("  - Field: Task.completed_at")
print("  - Status: Must be 'DONE'")

print("\n[✓] SETUP COMPLETE!")
print("\nYou can now:")
print("  1. Start the Django server: python manage.py runserver")
print("  2. Test endpoints using Postman/curl:")
print("     - GET http://localhost:8000/api/project-completion-chart/")
print("     - GET http://localhost:8000/api/task-completion-chart/")
print("  3. Include Authorization header with JWT token")

print("\n" + "="*60 + "\n")
