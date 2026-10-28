import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole, Patient, Doctor
from app.models.link import DoctorPatientLink, LinkStatus
from app.models.consent import ConsentRecord
from app.schemas.consent import ConsentGrantRequest, ConsentResponse
from app.audit.service import log_action

router = APIRouter(prefix="/consent", tags=["consent"])


def build_consent_response(consent: ConsentRecord, db: Session) -> ConsentResponse:
    resp = ConsentResponse.model_validate(consent)
    doctor = db.query(Doctor).filter(Doctor.id == consent.doctor_id).first()
    if doctor:
        resp.doctor_name = doctor.full_name
        resp.doctor_specialty = doctor.specialization
    patient = db.query(Patient).filter(Patient.id == consent.patient_id).first()
    if patient:
        resp.patient_name = patient.full_name
    return resp


@router.post("/grant", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
def grant_consent(
    payload: ConsentGrantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can grant consent",
        )

    patient_profile = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    doctor = db.query(Doctor).filter(Doctor.id == payload.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    # Access requires an active doctor-patient link
    link = db.query(DoctorPatientLink).filter(
        DoctorPatientLink.doctor_id == payload.doctor_id,
        DoctorPatientLink.patient_id == patient_profile.id,
        DoctorPatientLink.status == LinkStatus.ACTIVE,
    ).first()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot grant consent without an active doctor-patient link",
        )

    now = datetime.now(timezone.utc)
    consent = ConsentRecord(
        patient_id=patient_profile.id,
        doctor_id=payload.doctor_id,
        scope=payload.scope or "all",
        granted_at=now,
        expires_at=payload.expires_at,
        revoked_at=None,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="GRANT_CONSENT",
        resource_type="consent",
        resource_id=str(consent.id),
        patient_id=patient_profile.id,
        details={"doctor_id": str(payload.doctor_id), "scope": consent.scope},
    )

    return build_consent_response(consent, db)


@router.post("/{consent_id}/revoke", response_model=ConsentResponse)
def revoke_consent(
    consent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only patients can revoke consent",
        )

    patient_profile = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    consent = db.query(ConsentRecord).filter(ConsentRecord.id == consent_id).first()
    if not consent or consent.patient_id != patient_profile.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consent record not found")

    consent.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(consent)

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="REVOKE_CONSENT",
        resource_type="consent",
        resource_id=str(consent.id),
        patient_id=patient_profile.id,
        details={"doctor_id": str(consent.doctor_id)},
    )

    return build_consent_response(consent, db)


@router.get("/my", response_model=list[ConsentResponse])
def my_consents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.PATIENT:
        patient_profile = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        consents = (
            db.query(ConsentRecord)
            .filter(ConsentRecord.patient_id == patient_profile.id)
            .order_by(desc(ConsentRecord.granted_at))
            .all()
        )
        patient_id = patient_profile.id
    elif current_user.role == UserRole.DOCTOR:
        doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        consents = (
            db.query(ConsentRecord)
            .filter(ConsentRecord.doctor_id == doctor_profile.id)
            .order_by(desc(ConsentRecord.granted_at))
            .all()
        )
        patient_id = None
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role")

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="READ_CONSENTS",
        resource_type="consent",
        patient_id=patient_id,
        details={"count": len(consents)},
    )

    return [build_consent_response(c, db) for c in consents]


@router.get("/patient/{patient_id}", response_model=list[ConsentResponse])
def get_patient_consents(
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
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role")

    consents = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.patient_id == patient_id)
        .order_by(desc(ConsentRecord.granted_at))
        .all()
    )

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="READ_PATIENT_CONSENTS",
        resource_type="consent",
        patient_id=patient_id,
        details={"count": len(consents)},
    )

    return [build_consent_response(c, db) for c in consents]
