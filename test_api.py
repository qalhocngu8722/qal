#!/usr/bin/env python3
"""
Simple script to test the API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health check endpoint"""
    print("\n=== Testing Health Check ===")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_login():
    """Test login endpoint"""
    print("\n=== Testing Login ===")
    response = requests.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": "demo@test.com", "password": "Demo@123"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Access Token: {data['access_token'][:50]}...")
        return data['access_token']
    else:
        print(f"Error: {response.text}")
        return None

def test_tags(token):
    """Test tags endpoint"""
    print("\n=== Testing Get Tags ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/tags", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Error: {response.text}")
    return response.status_code == 200

def test_create_tag(token):
    """Test create tag endpoint"""
    print("\n=== Testing Create Tag ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/api/v1/tags",
        headers=headers,
        json={"name": "Work", "color": "#FF5733"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code in [200, 201]:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_todos(token):
    """Test todos endpoint"""
    print("\n=== Testing Get Todos ===")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/api/v1/todos", headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Total Todos: {data['total']}")
        print(f"First 3 todos: {json.dumps(data['items'][:3], indent=2)}")
    else:
        print(f"Error: {response.text}")
    return response.status_code == 200

if __name__ == "__main__":
    print("🚀 Starting API Tests...")
    
    # Test health
    if not test_health():
        print("❌ Health check failed!")
        exit(1)
    
    # Test login
    token = test_login()
    if not token:
        print("❌ Login failed!")
        exit(1)
    
    # Test tags
    if not test_tags(token):
        print("❌ Get tags failed!")
        exit(1)
    
    # Test create tag
    if not test_create_tag(token):
        print("⚠️ Create tag failed (might already exist)")
    
    # Test todos
    if not test_todos(token):
        print("❌ Get todos failed!")
        exit(1)
    
    print("\n✅ All tests passed!")
