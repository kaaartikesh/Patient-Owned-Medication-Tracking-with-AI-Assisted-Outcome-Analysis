import os
os.environ["JWT_SECRET"] = "super-secret-key-at-least-32-chars-long-test-123456"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure all models are registered on Base.metadata
from app.models import (  # noqa: F401
    user,
    link,
    encounter,
    medication,
    audit,
    consent,
    interaction,
    effectiveness,
)
from app.database import Base, get_db
from app.main import app

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Create all tables on the static test engine immediately
Base.metadata.create_all(bind=test_engine)

client = TestClient(app)
