#!/usr/bin/env python
"""Test custom task endpoint via direct HTTP request"""
import requests
import json
from datetime import date

BASE_URL = "http://localhost:8000/api"

# Test data matching frontend payload
test_data = {
    'title': 'auth',
    'plan_date': str(date.today()),
    'description': '',
    'planned_duration_minutes': 60,
    'quadrant': 'Q1',
    'is_unplanned': False,
    'scheduled_start_time': None,
    'user_id': '45'
}

print("=" * 60)
print("TEST: Custom Task Endpoint (HTTP Request)")
print("=" * 60)

print(f"\n→ Target URL: POST {BASE_URL}/today-plan/add_custom/")
print(f"→ Payload:")
print(json.dumps(test_data, indent=2))

try:
    response = requests.post(
        f"{BASE_URL}/today-plan/add_custom/",
        json=test_data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"\n✓ Status Code: {response.status_code}")
    print(f"✓ Response:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
        
except requests.exceptions.ConnectionError:
    print("\n✗ Error: Could not connect to server")
    print("   Make sure the Django development server is running")
    print("   Run: cd c:\\work\\das\\DAS_Backend\\activity && python manage.py runserver")
except Exception as e:
    print(f"\n✗ Error: {str(e)}")
