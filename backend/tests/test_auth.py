# backend/tests/test_auth.py

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db

# Use an in-memory SQLite database for fast, isolated test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

# Create a dedicated SQLAlchemy engine for testing with static pooling
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Configure a local session factory bound to the test database engine
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency override function to substitute the production database with the test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Force FastAPI to use the test database session override during requests
app.dependency_overrides[get_db] = override_get_db

# Initialize the TestClient wrapper to simulate HTTP requests against the FastAPI app
client = TestClient(app)

# Automatically create all database tables in memory before running any tests in this module
def setup_module(module):
    Base.metadata.create_all(bind=engine)

# Clean up and drop all tables from the in-memory database after module execution completes
def teardown_module(module):
    Base.metadata.drop_all(bind=engine)

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
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testpatient@gmail.com"
    assert "id" in data

# Test user login endpoint to confirm OAuth2 token generation and credential validation
def test_login_user():
    # OAuth2PasswordRequestForm expects form-encoded parameters (username & password)
    response = client.post(
        "/auth/login",
        data={
            "username": "testpatient@gmail.com",
            "password": "securepassword123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"