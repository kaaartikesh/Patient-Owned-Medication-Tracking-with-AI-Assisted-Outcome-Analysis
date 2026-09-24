# backend/app/auth/router.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.auth.security import hash_password, verify_password, create_access_token

# Groups every auth endpoint under one router, mounted in main.py
router = APIRouter(prefix="/auth", tags=["auth"])


# Creates a new User row after checking the email isn't already taken
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    new_user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# Verifies credentials and issues a signed JWT on success
@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    return TokenResponse(access_token=access_token)


# ---------------------------------------------------------------------------
# Project context: this file is the HTTP entry point tying together all
# three teammates' work — it validates input against schemas/auth.py,
# reads/writes models/user.py's User table, and calls auth/security.py to
# hash passwords and mint JWTs. The token's "sub" claim carries user.id and
# "role" carries the UserRole, which is what later middleware (e.g. the
# Encounter Engine) will decode to authorize requests.
#
# Known scope limit: register() only creates a User row, not a linked
# Patient/Doctor profile — RegisterRequest doesn't collect full_name yet,
# and that field is required on both. Extending registration to create
# the profile row is a task for a later phase, not milestone 1.
# ---------------------------------------------------------------------------