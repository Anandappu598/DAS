import requests
import json

# Define the endpoint
url = "http://localhost:8000/api/projects/create-with-tasks/"

# Define the payload
payload = {
    "name": "Test Project 500",
    "description": "Test Descr",
    "start_date": "2026-03-20",
    "deadline": "2026-03-25",
    "tasks": []
}

# Define headers
headers = {
    "Content-Type": "application/json"
}

# Make the request - assuming no auth for now, or use a known token if needed
# The view allows unauthenticated if configured, but let's see.
# Wait, permission_classes = [IsAuthenticated] !!
# We need a token.

# Let's try to login first? Or just mock a token if I know the secret.
# Or I can temporily change permission to AllowAny in views.py

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
