#backend/app/schemas/auth.py

# backend/app/schemas/auth.py

import uuid
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole

# Shape of the JSON body required for the POST /register endpoint
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole

# Shape of the JSON body required for the POST /login endpoint
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# Shape of the JSON returned after a user successfully logs in
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Shape of the JSON returned when we want to send user data back
class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: UserRole

    # Tells Pydantic to read data directly from the SQLAlchemy ORM models
    class Config:
        from_attributes = True

"""
This file defines the exact data boundaries for the authentication layer of the Patient Medication History System[cite: 1].
Just like a rule-based engine requires strictly formatted inputs to accurately process symptoms, these Pydantic models ensure the API only accepts correctly structured data, automatically rejecting any malformed requests before they reach the database.
"""