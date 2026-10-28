import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole, Patient, Doctor
from app.models.link import DoctorPatientLink, LinkStatus
from app.models.audit import AuditLog
from app.schemas.audit import AuditLogResponse
from app.audit.service import log_action

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/{patient_id}", response_model=list[AuditLogResponse])
def get_patient_audit_log(
    patient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve audit history for a patient.
    Accessible by the patient themselves, or a linked doctor.
    """
    if current_user.role == UserRole.PATIENT:
        patient_profile = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient_profile or patient_profile.id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access another patient's audit log",
            )
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
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No active link to this patient",
            )
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role")

    records = (
        db.query(AuditLog)
        .filter(AuditLog.patient_id == patient_id)
        .order_by(desc(AuditLog.timestamp))
        .all()
    )

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="READ_AUDIT_LOG",
        resource_type="audit_log",
        resource_id=str(patient_id),
        patient_id=patient_id,
        details={"record_count": len(records)},
    )

    return records
