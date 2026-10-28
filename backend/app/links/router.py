import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole, Patient, Doctor
from app.models.link import DoctorPatientLink, LinkStatus
from app.models.consent import ConsentRecord
from app.schemas.link import LinkRequest, LinkResponse
from app.audit.service import log_action

router = APIRouter(prefix="/links", tags=["links"])


def build_link_response(link: DoctorPatientLink, db: Session) -> LinkResponse:
    resp = LinkResponse.model_validate(link)
    doctor = db.query(Doctor).filter(Doctor.id == link.doctor_id).first()
    if doctor:
        resp.doctor_name = doctor.full_name
        resp.doctor_specialty = doctor.specialization
        if doctor.user:
            resp.doctor_email = doctor.user.email
    patient = db.query(Patient).filter(Patient.id == link.patient_id).first()
    if patient:
        resp.patient_name = patient.full_name
        if patient.user:
            resp.patient_email = patient.user.email
    return resp


@router.post("/request", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
def request_link(payload: LinkRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only doctors can request a link")

    doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor profile not found")

    patient_user = db.query(User).filter(User.email == payload.patient_email).first()
    if not patient_user or patient_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient with this email not found")

    patient_profile = db.query(Patient).filter(Patient.user_id == patient_user.id).first()
    if not patient_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    existing = db.query(DoctorPatientLink).filter(
        DoctorPatientLink.doctor_id == doctor_profile.id,
        DoctorPatientLink.patient_id == patient_profile.id,
    ).first()
    if existing:
        if existing.status == LinkStatus.REVOKED:
            existing.status = LinkStatus.PENDING
            db.commit()
            db.refresh(existing)
            return build_link_response(existing, db)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link already requested or active")

    link = DoctorPatientLink(doctor_id=doctor_profile.id, patient_id=patient_profile.id, status=LinkStatus.PENDING)
    db.add(link)
    db.commit()
    db.refresh(link)

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="REQUEST_LINK",
        resource_type="doctor_patient_link",
        resource_id=str(link.id),
        patient_id=patient_profile.id,
        details={"doctor_id": str(doctor_profile.id), "patient_email": payload.patient_email},
    )

    return build_link_response(link, db)


@router.post("/{link_id}/approve", response_model=LinkResponse)
def approve_link(link_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.PATIENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only patients can approve a link")

    patient_profile = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")

    link = db.query(DoctorPatientLink).filter(DoctorPatientLink.id == link_id).first()
    if not link or link.patient_id != patient_profile.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    link.status = LinkStatus.ACTIVE
    db.commit()
    db.refresh(link)

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="APPROVE_LINK",
        resource_type="doctor_patient_link",
        resource_id=str(link.id),
        patient_id=patient_profile.id,
        details={"doctor_id": str(link.doctor_id)},
    )

    return build_link_response(link, db)


@router.post("/{link_id}/reject", response_model=LinkResponse)
def reject_link(link_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    link = db.query(DoctorPatientLink).filter(DoctorPatientLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    if current_user.role == UserRole.PATIENT:
        patient_profile = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient_profile or link.patient_id != patient_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    elif current_user.role == UserRole.DOCTOR:
        doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor_profile or link.doctor_id != doctor_profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized")

    link.status = LinkStatus.REVOKED

    # Invalidate active consents so old consent never silently reactivates on relink
    active_consents = db.query(ConsentRecord).filter(
        ConsentRecord.patient_id == link.patient_id,
        ConsentRecord.doctor_id == link.doctor_id,
        ConsentRecord.revoked_at.is_(None),
    ).all()
    now = datetime.now(timezone.utc)
    for c in active_consents:
        c.revoked_at = now

    db.commit()
    db.refresh(link)

    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="REVOKE_LINK",
        resource_type="doctor_patient_link",
        resource_id=str(link.id),
        patient_id=link.patient_id,
        details={"doctor_id": str(link.doctor_id)},
    )

    return build_link_response(link, db)


@router.get("/my", response_model=list[LinkResponse])
def my_links(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.DOCTOR:
        doctor_profile = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
        if not doctor_profile:
            return []
        links = db.query(DoctorPatientLink).filter(DoctorPatientLink.doctor_id == doctor_profile.id).all()
        log_action(db, current_user.id, "READ_LINKS", "doctor_patient_link", details={"count": len(links)})
        return [build_link_response(l, db) for l in links]
    else:
        patient_profile = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient_profile:
            return []
        links = db.query(DoctorPatientLink).filter(DoctorPatientLink.patient_id == patient_profile.id).all()
        log_action(db, current_user.id, "READ_LINKS", "doctor_patient_link", patient_id=patient_profile.id, details={"count": len(links)})
        return [build_link_response(l, db) for l in links]