# backend/app/models/user.py

import enum
import uuid
from datetime import datetime 

from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Role values used across the system to distinguish patients from doctors
class UserRole(str, enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"


# Shared identity table — one row per person, patient or doctor
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    patient_profile: Mapped["Patient"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    doctor_profile: Mapped["Doctor"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"


# Patient-specific profile fields, linked 1:1 to a User row
class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    phone_number: Mapped[str] = mapped_column(String(20), nullable=True)

    user: Mapped["User"] = relationship(back_populates="patient_profile")

    def __repr__(self) -> str:
        return f"<Patient id={self.id} full_name={self.full_name}>"


# Doctor-specific profile fields, linked 1:1 to a User row
class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialization: Mapped[str] = mapped_column(String(255), nullable=True)
    license_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="doctor_profile")

    def __repr__(self) -> str:
        return f"<Doctor id={self.id} full_name={self.full_name}>"


# ---------------------------------------------------------------------------
# Project context: `users` is the shared auth table auth/security.py queries
# at login and encodes into the JWT (sub = user.id). `patients` and `doctors`
# hold only role-specific fields and are what every later table (encounters,
# medication_entries, doctor_patient_link, etc.) will foreign-key against.
# `uselist=False` overrides SQLAlchemy's default many-side assumption since
# each user has exactly one profile; cascade="all, delete-orphan" plus
# ondelete="CASCADE" keep that profile row cleaned up at both the ORM and DB
# level if the user is deleted. Requires `Base` from app/database.py (not
# yet created) — someone needs to define `Base = declarative_base()` there.
# ---------------------------------------------------------------------------