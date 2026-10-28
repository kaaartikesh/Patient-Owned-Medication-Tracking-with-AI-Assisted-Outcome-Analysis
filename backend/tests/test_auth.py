# backend/tests/test_auth.py

from tests.conftest import client, TestingSessionLocal

# Test the basic liveness check endpoint to ensure application startup is healthy
def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# Test user registration endpoint to verify data persistence and response structure
def test_register_user():
    response = client.post(
        "/auth/register",
        json={
            "email": "testpatient@gmail.com",
            "password": "securepassword123",
            "full_name": "Test Patient",
            "role": "patient"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testpatient@gmail.com"
    assert "id" in data

# Test user login endpoint to confirm OAuth2 token generation and credential validation
def test_login_user():
    response = client.post(
        "/auth/login",
        json={
            "email": "testpatient@gmail.com",
            "password": "securepassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"