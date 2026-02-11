"""
Test cases for Project Work Stats API endpoints

Run these tests after starting the Django server:
python manage.py runserver

Make sure you have:
1. Created users with different roles
2. Created projects with handled_by field set
3. Created tasks for those projects
4. Set some tasks to completed status
"""

# Test URLs
BASE_URL = "http://localhost:8000/api/dashboard"

# Sample test scenarios

"""
SCENARIO 1: Admin User Testing
-------------------------------
1. Login as ADMIN user to get access token
2. Call GET /api/dashboard/users-for-stats/
   Expected: Should return all active users
3. Call GET /api/dashboard/project-work-stats/?user_id=<any_user_id>
   Expected: Should return project stats for that user

SCENARIO 2: Manager/TeamLead Testing
------------------------------------
1. Login as MANAGER/TEAMLEAD user to get access token
2. Call GET /api/dashboard/users-for-stats/
   Expected: Should return only users from same department
3. Call GET /api/dashboard/project-work-stats/?user_id=<user_from_same_dept>
   Expected: Should return project stats
4. Call GET /api/dashboard/project-work-stats/?user_id=<user_from_different_dept>
   Expected: Should return 403 Forbidden error

SCENARIO 3: Employee Testing
----------------------------
1. Login as EMPLOYEE user to get access token
2. Call GET /api/dashboard/users-for-stats/
   Expected: Should return only the employee themselves
3. Call GET /api/dashboard/project-work-stats/
   Expected: Should return their own project stats
4. Call GET /api/dashboard/project-work-stats/?user_id=<other_user_id>
   Expected: Should return 403 Forbidden error

SCENARIO 4: User with No Projects
---------------------------------
1. Login as user with no projects assigned in handled_by
2. Call GET /api/dashboard/project-work-stats/
   Expected: Should return message "No projects handled by this user."

SCENARIO 5: Verify Calculation Logic
------------------------------------
Create a test project with:
- 10 total tasks
- 4 tasks with status='DONE'
- 6 tasks with status='PENDING' or 'IN_PROGRESS'

Call the API for the user who handles this project
Expected completion_percentage: 40%
"""

# Example Python test using requests library

import requests

def test_project_work_stats():
    """
    Example test function using Python requests
    
    Prerequisites:
    - pip install requests
    - Django server running
    - Valid user credentials
    """
    
    # Step 1: Login to get access token
    login_url = "http://localhost:8000/api/login/"
    login_data = {
        "email": "admin@example.com",  # Replace with your admin email
        "password": "password123"       # Replace with your password
    }
    
    login_response = requests.post(login_url, json=login_data)
    if login_response.status_code == 200:
        access_token = login_response.json()['access']
        print(f"✓ Login successful")
    else:
        print(f"✗ Login failed: {login_response.text}")
        return
    
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    
    # Step 2: Get users for stats
    users_url = f"{BASE_URL}/users-for-stats/"
    users_response = requests.get(users_url, headers=headers)
    
    if users_response.status_code == 200:
        users_data = users_response.json()
        print(f"✓ Users retrieved: {users_data['count']} users")
        print(f"  Users: {[u['name'] for u in users_data['users']]}")
        
        # Step 3: Get stats for first user
        if users_data['count'] > 0:
            first_user_id = users_data['users'][0]['id']
            stats_url = f"{BASE_URL}/project-work-stats/?user_id={first_user_id}"
            stats_response = requests.get(stats_url, headers=headers)
            
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                print(f"✓ Project stats retrieved for {stats_data['user']['name']}")
                print(f"  Overall completion: {stats_data['overall_completion_percentage']}%")
                print(f"  Total projects: {stats_data['total_projects']}")
                print(f"  Total tasks: {stats_data['total_tasks']}")
                print(f"  Completed tasks: {stats_data['completed_tasks']}")
                print(f"\n  Projects breakdown:")
                for project in stats_data['projects']:
                    print(f"    - {project['name']}: {project['completion_percentage']}% " +
                          f"({project['completed_tasks']}/{project['total_tasks']} tasks)")
            else:
                print(f"✗ Failed to get project stats: {stats_response.text}")
    else:
        print(f"✗ Failed to get users: {users_response.text}")


# cURL examples for quick testing

"""
# 1. Login (replace with your credentials)
curl -X POST http://localhost:8000/api/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123"}'

# Copy the access token from the response

# 2. Get users for dropdown
curl -X GET http://localhost:8000/api/dashboard/users-for-stats/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"

# 3. Get project stats for a specific user
curl -X GET "http://localhost:8000/api/dashboard/project-work-stats/?user_id=2" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"

# 4. Get project stats for current logged-in user
curl -X GET http://localhost:8000/api/dashboard/project-work-stats/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
"""

# JavaScript/Fetch API examples

"""
// 1. Login
const loginResponse = await fetch('http://localhost:8000/api/login/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        email: 'admin@example.com',
        password: 'password123'
    })
});
const loginData = await loginResponse.json();
const token = loginData.access;

// 2. Get users for dropdown
const usersResponse = await fetch('http://localhost:8000/api/dashboard/users-for-stats/', {
    headers: { 'Authorization': `Bearer ${token}` }
});
const usersData = await usersResponse.json();
console.log('Users:', usersData);

// 3. Get project stats
const statsResponse = await fetch(`http://localhost:8000/api/dashboard/project-work-stats/?user_id=2`, {
    headers: { 'Authorization': `Bearer ${token}` }
});
const statsData = await statsResponse.json();
console.log('Project Stats:', statsData);
"""

if __name__ == "__main__":
    print("=" * 60)
    print("PROJECT WORK STATS API TESTS")
    print("=" * 60)
    print("\nRunning tests...\n")
    
    try:
        test_project_work_stats()
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        print("\nMake sure:")
        print("  1. Django server is running (python manage.py runserver)")
        print("  2. You have 'requests' library installed (pip install requests)")
        print("  3. You have valid user credentials in the test")
