import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User, UserRole, Patient, Doctor
from app.models.link import DoctorPatientLink, LinkStatus
from app.models.encounter import Encounter
from app.models.medication import MedicationEntry
from app.models.interaction import InteractionFlag
from app.models.effectiveness import EffectivenessLog
from app.consent.service import has_active_consent
from app.audit.service import log_action
from app.export.pdf_service import generate_patient_history_pdf

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/{patient_id}")
def export_patient_history(
    patient_id: uuid.UUID,
    format: Literal["json", "pdf"] = Query("json", description="Export format: json or pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export unified medication history, encounters, effectiveness logs, and interaction flags.
    Allowed for the patient themselves or a linked doctor with active consent.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Access control
    if current_user.role == UserRole.PATIENT:
        patient_profile = db.query(Patient).filter(Patient.user_id == current_user.id).first()
        if not patient_profile or patient_profile.id != patient_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot export another patient's data")
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
                detail="No active consent from patient to export medical history",
            )
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized role")

    # Gather Medications
    medications = (
        db.query(MedicationEntry)
        .filter(MedicationEntry.patient_id == patient_id)
        .order_by(desc(MedicationEntry.created_at))
        .all()
    )
    med_list = []
    for m in medications:
        doc_name = None
        if m.doctor_id:
            d = db.query(Doctor).filter(Doctor.id == m.doctor_id).first()
            if d:
                doc_name = f"Dr. {d.full_name}"
        med_list.append(
            {
                "id": str(m.id),
                "medication_name": m.medication_name,
                "dosage": m.dosage,
                "frequency": m.frequency,
                "notes": m.notes,
                "doctor_id": str(m.doctor_id) if m.doctor_id else None,
                "doctor_name": doc_name,
                "encounter_id": str(m.encounter_id) if m.encounter_id else None,
                "start_date": m.start_date.isoformat() if m.start_date else None,
                "end_date": m.end_date.isoformat() if m.end_date else None,
                "is_active": m.is_active,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
        )

    # Gather Encounters
    encounters = (
        db.query(Encounter)
        .filter(Encounter.patient_id == patient_id)
        .order_by(desc(Encounter.started_at))
        .all()
    )
    enc_list = []
    for e in encounters:
        d = db.query(Doctor).filter(Doctor.id == e.doctor_id).first()
        doc_name = f"Dr. {d.full_name}" if d else "Doctor"
        enc_list.append(
            {
                "id": str(e.id),
                "doctor_id": str(e.doctor_id),
                "doctor_name": doc_name,
                "status": e.status.value if hasattr(e.status, "value") else str(e.status),
                "started_at": e.started_at.isoformat() if e.started_at else None,
                "expires_at": e.expires_at.isoformat() if e.expires_at else None,
                "notes": e.notes,
            }
        )

    # Gather Effectiveness Logs
    eff_logs = (
        db.query(EffectivenessLog)
        .filter(EffectivenessLog.patient_id == patient_id)
        .order_by(desc(EffectivenessLog.logged_at))
        .all()
    )
    eff_list = []
    for el in eff_logs:
        eff_list.append(
            {
                "id": str(el.id),
                "medication_entry_id": str(el.medication_entry_id),
                "medication_name": el.medication.medication_name if el.medication else "Medication",
                "rating": el.rating,
                "side_effects": el.side_effects,
                "logged_at": el.logged_at.isoformat() if el.logged_at else None,
            }
        )

    # Gather Interaction Flags
    flags = (
        db.query(InteractionFlag)
        .filter(InteractionFlag.patient_id == patient_id)
        .order_by(desc(InteractionFlag.created_at))
        .all()
    )
    flag_list = []
    for f in flags:
        flag_list.append(
            {
                "id": str(f.id),
                "medication_a_id": str(f.medication_a_id),
                "medication_a_name": f.medication_a.medication_name if f.medication_a else None,
                "medication_b_id": str(f.medication_b_id),
                "medication_b_name": f.medication_b.medication_name if f.medication_b else None,
                "severity": f.severity,
                "description": f.description,
                "status": f.status,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
        )

    export_payload = {
        "patient": {
            "id": str(patient.id),
            "full_name": patient.full_name,
            "email": patient.user.email if patient.user else "",
            "phone_number": patient.phone_number,
            "date_of_birth": patient.date_of_birth.isoformat() if patient.date_of_birth else None,
        },
        "medications": med_list,
        "encounters": enc_list,
        "effectiveness_logs": eff_list,
        "interaction_flags": flag_list,
    }

    # Audit log entry for export action
    log_action(
        db=db,
        actor_user_id=current_user.id,
        action="EXPORT_HISTORY",
        resource_type="export",
        resource_id=str(patient_id),
        patient_id=patient_id,
        details={
            "format": format,
            "medication_count": len(med_list),
            "encounter_count": len(enc_list),
            "flag_count": len(flag_list),
            "effectiveness_count": len(eff_list),
        },
    )

    if format == "pdf":
        pdf_bytes = generate_patient_history_pdf(export_payload)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="patient_history_{patient_id}.pdf"'
            },
        )

    return export_payload
