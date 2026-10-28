import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole, Doctor, Patient
from app.models.link import DoctorPatientLink, LinkStatus
from app.models.encounter import Encounter, EncounterStatus
from app.models.medication import MedicationEntry
from app.schemas.medication import MedicationCreateRequest, MedicationResponse
from app.schemas.interaction import InteractionFlagResponse
from app.consent.service import has_active_consent
from app.interactions.service import check_and_create_interactions
from app.audit.service import log_action

router = APIRouter(prefix="/medications", tags=["medications"])


@router.post("", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
def add_medication(
    payload: MedicationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.PATIENT:
        patient_profile = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient_profile or patient_profile.id != payload.patient_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot log medication for another patient")
        doctor_id = None
        encounter_id = None

    elif current_user.role == UserRole.DOCTOR:
        doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor_profile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor profile not found")

        if not payload.encounter_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Doctors must log medications inside an active encounter",
            )

        encounter = db.query(Encounter).filter(Encounter.id == payload.encounter_id).first()
        if not encounter or encounter.doctor_id != doctor_profile.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Encounter not found")

        now = datetime.now(timezone.utc)
        encounter_expiry = (
            encounter.expires_at.replace(tzinfo=timezone.utc)
            if encounter.expires_at.tzinfo is None
            else encounter.expires_at
        )

        if encounter.status != EncounterStatus.ACTIVE or encounter_expiry < now:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Encounter write window has expired")
        if encounter.patient_id != payload.patient_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Encounter does not match patient")

        doctor_id = doctor_profile.id
        encounter_id = encounter.id

    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unsupported role")

    start_date = payload.start_date or datetime.now(timezone.utc)

    entry = MedicationEntry(
        patient_id=payload.patient_id,
        doctor_id=doctor_id,
        encounter_id=encounter_id,
        medication_name=payload.medication_name,
        dosage=payload.dosage,
        frequency=payload.frequency,
        notes=payload.notes,
        start_date=start_date,
        end_date=payload.end_date,
        is_active=payload.is_active,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    # Cross-doctor drug interaction check
    flag_records = check_and_create_interactions(db, entry)

    flag_responses = []
    for f in flag_records:
        fr = InteractionFlagResponse.model_validate(f)
        fr.medication_a_name = f.medication_a.medication_name if f.medication_a else None
        fr.medication_b_name = f.medication_b.medication_name if f.medication_b else None
        flag_responses.append(fr)

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="ADD_MEDICATION",
        resource_type="medication_entry",
        resource_id=str(entry.id),
        patient_id=payload.patient_id,
        details={
            "medication_name": entry.medication_name,
            "interaction_flags_triggered": len(flag_responses),
        },
    )

    response_data = MedicationResponse.model_validate(entry)
    response_data.interaction_flags = flag_responses
    return response_data


@router.get("/{patient_id}", response_model=list[MedicationResponse])
def list_medications(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.PATIENT:
        patient_profile = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient_profile or patient_profile.id != patient_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view another patient's medications")

    elif current_user.role == UserRole.DOCTOR:
        doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor_profile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor profile not found")

        link = db.query(DoctorPatientLink).filter(
            DoctorPatientLink.doctor_id == doctor_profile.id,
            DoctorPatientLink.patient_id == patient_id,
            DoctorPatientLink.status == LinkStatus.ACTIVE,
        ).first()
        if not link:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active link to this patient")

        # Enforce consent for doctor medication read
        if not has_active_consent(db, patient_id, doctor_profile.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No active consent from patient to view medications",
            )
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unsupported role")

    entries = (
        db.query(MedicationEntry)
        .filter(MedicationEntry.patient_id == patient_id)
        .order_by(desc(MedicationEntry.created_at))
        .all()
    )

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="READ_MEDICATIONS",
        resource_type="medication_entry",
        patient_id=patient_id,
        details={"count": len(entries)},
    )

    return entries