import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole, Patient, Doctor
from app.models.link import DoctorPatientLink, LinkStatus
from app.models.interaction import InteractionFlag
from app.schemas.interaction import InteractionFlagResponse
from app.consent.service import has_active_consent
from app.audit.service import log_action

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("/{patient_id}", response_model=list[InteractionFlagResponse])
def get_patient_interactions(
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
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No active consent from patient")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role")

    flags = (
        db.query(InteractionFlag)
        .filter(InteractionFlag.patient_id == patient_id)
        .order_by(desc(InteractionFlag.created_at))
        .all()
    )

    result = []
    for f in flags:
        resp = InteractionFlagResponse.model_validate(f)
        resp.medication_a_name = f.medication_a.medication_name if f.medication_a else None
        resp.medication_b_name = f.medication_b.medication_name if f.medication_b else None
        result.append(resp)

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="READ_INTERACTIONS",
        resource_type="interaction_flags",
        patient_id=patient_id,
        details={"flag_count": len(result)},
    )

    return result
