import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole, Doctor, Patient
from app.models.link import DoctorPatientLink, LinkStatus
from app.models.encounter import Encounter, EncounterStatus
from app.schemas.encounter import EncounterStartRequest, EncounterResponse
from app.consent.service import has_active_consent
from app.audit.service import log_action

router = APIRouter(prefix="/encounters", tags=["encounters"])


def build_encounter_response(encounter: Encounter, db: Session) -> EncounterResponse:
    resp = EncounterResponse.model_validate(encounter)
    doctor = db.query(Doctor).filter(Doctor.id == encounter.doctor_id).first()
    if doctor:
        resp.doctor_name = doctor.full_name
    patient = db.query(Patient).filter(Patient.id == encounter.patient_id).first()
    if patient:
        resp.patient_name = patient.full_name
    return resp


@router.post("/start", response_model=EncounterResponse, status_code=status.HTTP_201_CREATED)
def start_encounter(
    payload: EncounterStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can start an encounter")

    doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor_profile:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor profile not found")

    link = db.query(DoctorPatientLink).filter(
        DoctorPatientLink.doctor_id == doctor_profile.id,
        DoctorPatientLink.patient_id == payload.patient_id,
        DoctorPatientLink.status == LinkStatus.ACTIVE,
    ).first()
    if not link:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active link to this patient")

    # Enforce active consent
    if not has_active_consent(db, payload.patient_id, doctor_profile.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active consent from this patient to start an encounter",
        )

    now = datetime.now(timezone.utc)
    encounter = Encounter(
        doctor_id=doctor_profile.id,
        patient_id=payload.patient_id,
        started_at=now,
        expires_at=now + timedelta(minutes=payload.duration_minutes),
        status=EncounterStatus.ACTIVE,
    )
    db.add(encounter)
    db.commit()
    db.refresh(encounter)

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="START_ENCOUNTER",
        resource_type="encounter",
        resource_id=str(encounter.id),
        patient_id=payload.patient_id,
        details={"duration_minutes": payload.duration_minutes, "expires_at": encounter.expires_at.isoformat()},
    )

    return build_encounter_response(encounter, db)


@router.post("/{encounter_id}/close", response_model=EncounterResponse)
def close_encounter(
    encounter_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can close an encounter")

    doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()

    encounter = db.query(Encounter).filter(Encounter.id == encounter_id).first()
    if not encounter or encounter.doctor_id != doctor_profile.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")

    encounter.status = EncounterStatus.CLOSED
    db.commit()
    db.refresh(encounter)

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="CLOSE_ENCOUNTER",
        resource_type="encounter",
        resource_id=str(encounter.id),
        patient_id=encounter.patient_id,
    )

    return build_encounter_response(encounter, db)


@router.get("/patient/{patient_id}", response_model=list[EncounterResponse])
def get_patient_encounters(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.PATIENT:
        patient_profile = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient_profile or patient_profile.id != patient_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    elif current_user.role == UserRole.DOCTOR:
        doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        link = db.query(DoctorPatientLink).filter(
            DoctorPatientLink.doctor_id == doctor_profile.id,
            DoctorPatientLink.patient_id == patient_id,
            DoctorPatientLink.status == LinkStatus.ACTIVE,
        ).first()
        if not link:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active link to this patient")
        if not has_active_consent(db, patient_id, doctor_profile.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active consent from this patient")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role")

    encounters = (
        db.query(Encounter)
        .filter(Encounter.patient_id == patient_id)
        .order_by(desc(Encounter.started_at))
        .all()
    )

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="READ_ENCOUNTERS",
        resource_type="encounter",
        patient_id=patient_id,
        details={"count": len(encounters)},
    )

    return [build_encounter_response(e, db) for e in encounters]