from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, Patient, Doctor, UserRole
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.auth.security import hash_password, verify_password, create_access_token
from app.audit.service import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


def user_full_name(user: User, db: Session) -> str:
    if user.role == UserRole.PATIENT:
        profile = db.query(Patient).filter(Patient.user_id == user.id).first()
    else:
        profile = db.query(Doctor).filter(Doctor.user_id == user.id).first()
    return profile.full_name if profile else ""


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

    if payload.role == UserRole.PATIENT:
        profile = Patient(user_id=new_user.id, full_name=payload.full_name)
    else:
        profile = Doctor(user_id=new_user.id, full_name=payload.full_name)

    db.add(profile)
    db.commit()
    db.refresh(profile)

    patient_id = profile.id if payload.role == UserRole.PATIENT else None
    log_action(
        db=db,
        actor_user_id=new_user.id,
        action="REGISTER",
        resource_type="user",
        resource_id=str(new_user.id),
        patient_id=patient_id,
        details={"email": new_user.email, "role": new_user.role.value},
    )

    return new_user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    full_name = user_full_name(user, db)
    patient_id = None
    doctor_id = None

    if user.role == UserRole.PATIENT:
        p = db.query(Patient).filter(Patient.user_id == user.id).first()
        if p:
            patient_id = str(p.id)
    else:
        d = db.query(Doctor).filter(Doctor.user_id == user.id).first()
        if d:
            doctor_id = str(d.id)

    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value,
            "name": full_name,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
        }
    )

    log_action(
        db=db,
        actor_user_id=user.id,
        action="LOGIN",
        resource_type="user",
        resource_id=str(user.id),
        details={"role": user.role.value},
    )

    return TokenResponse(access_token=access_token)


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns profile information for the authenticated user."""
    profile_data = {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "name": user_full_name(current_user, db),
    }
    if current_user.role == UserRole.PATIENT:
        p = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        profile_data["patient_id"] = str(p.id) if p else None
    else:
        d = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        profile_data["doctor_id"] = str(d.id) if d else None

    return profile_data