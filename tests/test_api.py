import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health_check():
    """Test that the API is up and running."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"

def test_frontend_routes():
    """Test that the UI is correctly mounted and served."""
    response = client.get("/ui")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_authentication_flow():
    """Test full registration and login flow for a user."""
    # Register
    test_user = {
        "name": "Test Student",
        "email": "teststudent@example.com",
        "password": "securepassword123"
    }
    reg_response = client.post("/api/auth/register", json=test_user)
    
    # If the user already exists from a previous test run, it might be 400
    if reg_response.status_code == 200:
        assert "token" in reg_response.json()
    else:
        assert reg_response.status_code == 400
        
    # Login
    login_data = {
        "email": "teststudent@example.com",
        "password": "securepassword123"
    }
    login_response = client.post("/api/auth/login", json=login_data)
    assert login_response.status_code == 200
    assert "token" in login_response.json()

    # Get Me
    token = login_response.json()["token"]
    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "teststudent@example.com"

def test_unauthorized_access():
    """Test that protected routes block unauthorized access."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
