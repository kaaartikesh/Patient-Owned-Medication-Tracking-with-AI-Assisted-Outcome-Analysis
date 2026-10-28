import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.consent import ConsentRecord


def get_active_consent(
    db: Session,
    patient_id: uuid.UUID,
    doctor_id: uuid.UUID,
    scope: Optional[str] = None,
) -> Optional[ConsentRecord]:
    """
    Checks if a doctor has valid, non-revoked, non-expired consent from a patient.
    """
    now = datetime.now(timezone.utc)
    query = db.query(ConsentRecord).filter(
        ConsentRecord.patient_id == patient_id,
        ConsentRecord.doctor_id == doctor_id,
        ConsentRecord.revoked_at.is_(None),
        or_(ConsentRecord.expires_at.is_(None), ConsentRecord.expires_at > now),
    )

    if scope and scope != "all":
        query = query.filter(or_(ConsentRecord.scope == "all", ConsentRecord.scope == scope))

    return query.first()


def has_active_consent(
    db: Session,
    patient_id: uuid.UUID,
    doctor_id: uuid.UUID,
    scope: Optional[str] = None,
) -> bool:
    return get_active_consent(db, patient_id, doctor_id, scope) is not None
