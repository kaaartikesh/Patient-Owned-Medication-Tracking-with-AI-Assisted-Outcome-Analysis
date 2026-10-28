import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole, Patient, Doctor
from app.models.link import DoctorPatientLink, LinkStatus
from app.models.medication import MedicationEntry
from app.models.effectiveness import EffectivenessLog
from app.schemas.effectiveness import EffectivenessCreateRequest, EffectivenessResponse
from app.consent.service import has_active_consent
from app.audit.service import log_action

router = APIRouter(prefix="/effectiveness", tags=["effectiveness"])


@router.post("", response_model=EffectivenessResponse, status_code=status.HTTP_201_CREATED)
def log_effectiveness(
    payload: EffectivenessCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can log medication effectiveness and side effects",
        )

    patient_profile = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    med_entry = db.query(MedicationEntry).filter(MedicationEntry.id == payload.medication_entry_id).first()
    if not med_entry or med_entry.patient_id != patient_profile.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medication entry not found for this patient",
        )

    now = datetime.now(timezone.utc)
    log_entry = EffectivenessLog(
        medication_entry_id=payload.medication_entry_id,
        patient_id=patient_profile.id,
        rating=payload.rating,
        side_effects=payload.side_effects,
        logged_at=now,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="LOG_EFFECTIVENESS",
        resource_type="effectiveness_log",
        resource_id=str(log_entry.id),
        patient_id=patient_profile.id,
        details={
            "medication_id": str(payload.medication_entry_id),
            "medication_name": med_entry.medication_name,
            "rating": payload.rating,
        },
    )

    resp = EffectivenessResponse.model_validate(log_entry)
    resp.medication_name = med_entry.medication_name
    return resp


@router.get("/patient/{patient_id}", response_model=list[EffectivenessResponse])
def get_patient_effectiveness_logs(
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
        if not doctor_profile:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor profile not found")

        link = db.query(DoctorPatientLink).filter(
            DoctorPatientLink.doctor_id == doctor_profile.id,
            DoctorPatientLink.patient_id == patient_id,
            DoctorPatientLink.status == LinkStatus.ACTIVE,
        ).first()
        if not link:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active link to this patient")

        if not has_active_consent(db, patient_id, doctor_profile.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No active consent from patient to read effectiveness logs",
            )
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role")

    logs = (
        db.query(EffectivenessLog)
        .filter(EffectivenessLog.patient_id == patient_id)
        .order_by(desc(EffectivenessLog.logged_at))
        .all()
    )

    result = []
    for l in logs:
        r = EffectivenessResponse.model_validate(l)
        r.medication_name = l.medication.medication_name if l.medication else None
        result.append(r)

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="READ_EFFECTIVENESS",
        resource_type="effectiveness_log",
        patient_id=patient_id,
        details={"count": len(result)},
    )

    return result


@router.get("/medication/{medication_id}", response_model=list[EffectivenessResponse])
def get_medication_effectiveness_logs(
    medication_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    med = db.query(MedicationEntry).filter(MedicationEntry.id == medication_id).first()
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medication not found")

    return get_patient_effectiveness_logs(med.patient_id, db=db, current_user=current_user)
