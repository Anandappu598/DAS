#!/usr/bin/env python
"""Test custom task endpoint to debug why data isn't being saved"""
import os
import sys
import django
from datetime import datetime, date

# Setup Django
sys.path.insert(0, '/work/das/DAS_Backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.activity.settings')
django.setup()

from django.contrib.auth import get_user_model
from activity.schedular.models import TodayPlan, ActivityLog
from rest_framework.test import APIRequestFactory
from activity.schedular.views import TodayPlanViewSet

User = get_user_model()

print("=" * 60)
print("TEST: Custom Task Endpoint")
print("=" * 60)

# Get or create a test user
user = User.objects.filter(role='USER').first()
if not user:
    user = User.objects.create_user(
        email=f'test_user_{datetime.now().timestamp()}@test.com',
        password='testpass123',
        first_name='Test',
        last_name='User',
        role='USER'
    )
    print(f"✓ Created test user: {user.id}")
else:
    print(f"✓ Using existing user: {user.id} ({user.email})")

# Clear any existing test data for today
today = date.today()
TodayPlan.objects.filter(user=user, plan_date=today).delete()
print(f"✓ Cleared previous test data for {today}")

# Prepare test data (matching frontend payload)
test_payload = {
    'title': 'auth',
    'plan_date': str(today),
    'description': '',
    'planned_duration_minutes': 60,
    'quadrant': 'Q1',
    'is_unplanned': False,
    'related_task_id': None,
    'scheduled_start_time': None,
    'user_id': str(user.id)
}

print(f"\n→ Test Payload:")
for key, value in test_payload.items():
    print(f"  {key}: {value}")

# Test the endpoint using APIRequestFactory
factory = APIRequestFactory()
viewset = TodayPlanViewSet()

# Create a POST request to the add_custom action
request = factory.post('/api/today-plan/add_custom/', test_payload, format='json')
request.user = user

# Set the action and user
viewset.action = 'add_custom'
viewset.request = request
viewset.format_kwarg = None

print(f"\n→ Calling endpoint: POST /api/today-plan/add_custom/")
try:
    response = viewset.add_custom(request)
    print(f"\n✓ Response Status: {response.status_code}")
    print(f"✓ Response Data:")
    import json
    resp_data = response.data
    print(json.dumps(resp_data, indent=2, default=str))
    
    # Verify it was saved
    saved_plans = TodayPlan.objects.filter(user=user, plan_date=today)
    print(f"\n✓ Plans saved in database: {saved_plans.count()}")
    for plan in saved_plans:
        print(f"  - ID: {plan.id}, Title: {plan.custom_title or plan.catalog_item}, Quadrant: {plan.quadrant}")
        
except Exception as e:
    print(f"\n✗ Error calling endpoint: {str(e)}")
    import traceback
    traceback.print_exc()

# Now test the add_from_catalog endpoint for comparison
print(f"\n\n" + "=" * 60)
print("INFO: add_from_catalog endpoint expects 'catalog_id' field")
print("=" * 60)
from activity.schedular.models import Catalog

catalog = Catalog.objects.first()
if catalog:
    print(f"✓ Found catalog item: {catalog.id} - {catalog.name}")
    
    catalog_payload = {
        'catalog_id': catalog.id,
        'plan_date': str(today),
        'quadrant': 'Q1',
        'is_unplanned': False
    }
    
    print(f"\n→ Catalog Payload:")
    for key, value in catalog_payload.items():
        print(f"  {key}: {value}")
    
    request2 = factory.post('/api/today-plan/add_from_catalog/', catalog_payload, format='json')
    request2.user = user
    viewset.request = request2
    
    print(f"\n→ Calling endpoint: POST /api/today-plan/add_from_catalog/")
    try:
        response2 = viewset.add_from_catalog(request2)
        print(f"\n✓ Response Status: {response2.status_code}")
        print(f"✓ Response Data (first 200 chars): {str(response2.data)[:200]}")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
else:
    print("✗ No catalog items found")

print(f"\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
