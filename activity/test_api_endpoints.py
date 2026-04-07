#!/usr/bin/env python
"""Test API endpoints to verify they return employee names correctly"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'activity.settings')
django.setup()

from schedular.models import User
from schedular.views import TeamInstructionViewSet, DashboardViewSet, TeamOverviewViewSet
from rest_framework.test import APIRequestFactory, force_authenticate

print("\n" + "="*80)
print("Testing API Endpoints - Employee Names")
print("="*80)

factory = APIRequestFactory()
admin_user = User.objects.filter(role='ADMIN').first()

# Test 1: project_members endpoint (TeamInstructionViewSet)
print("\n1. project_members endpoint (TeamInstructionViewSet):")
request1 = factory.get('/api/team-instructions/project_members/')
force_authenticate(request1, user=admin_user)

viewset1 = TeamInstructionViewSet.as_view({'get': 'project_members'})
response1 = viewset1(request1)

print(f"   Status: {response1.status_code}")
if response1.status_code == 200:
    members = response1.data.get('members', [])[:5]
    for member in members:
        print(f"   - {member.get('email'):40} -> '{member.get('name', 'MISSING')}'")

# Test 2: users_for_stats endpoint (DashboardViewSet)
print("\n2. users_for_stats endpoint (DashboardViewSet):")
request2 = factory.get('/api/dashboard/users-for-stats/')
force_authenticate(request2, user=admin_user)

viewset2 = DashboardViewSet.as_view({'get': 'users_for_stats'})
response2 = viewset2(request2)

print(f"   Status: {response2.status_code}")
if response2.status_code == 200:
    users = response2.data.get('users', [])[:5]
    for user in users:
        print(f"   - {user.get('email'):40} -> '{user.get('name', 'MISSING')}'")

# Test 3: team_members endpoint (TeamOverviewViewSet) with all_users=true
print("\n3. team_members endpoint (TeamOverviewViewSet, all_users=true):")
request3 = factory.get('/api/team-overview/team_members/', {'all_users': 'true'})
force_authenticate(request3, user=admin_user)

viewset3 = TeamOverviewViewSet.as_view({'get': 'team_members'})
response3 = viewset3(request3)

print(f"   Status: {response3.status_code}")
if response3.status_code == 200:
    members = response3.data.get('members', [])[:5]
    for member in members:
        print(f"   - {member.get('email'):40} -> '{member.get('name', 'MISSING')}'")

# Test 4: team_activity_status endpoint (DashboardViewSet)
print("\n4. team_activity_status endpoint (DashboardViewSet):")
request4 = factory.get('/api/dashboard/team-activity-status/')
force_authenticate(request4, user=admin_user)

viewset4 = DashboardViewSet.as_view({'get': 'team_activity_status'})
response4 = viewset4(request4)

print(f"   Status: {response4.status_code}")
if response4.status_code == 200:
    users = response4.data.get('users', [])[:3]
    for user in users:
        print(f"   - {user.get('email'):40} -> '{user.get('name', 'MISSING')}'")

print("\n" + "="*80)
