import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.audit import AuditLog


def log_action(
    db: Session,
    actor_user_id: Optional[uuid.UUID],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    patient_id: Optional[uuid.UUID] = None,
    details: Optional[Any] = None,
) -> AuditLog:
    """
    Appends a new immutable, tamper-evident audit record to audit_log with cryptographic hash chaining.
    """
    # Fetch the most recent audit entry to link the hash chain
    latest_entry = db.query(AuditLog).order_by(desc(AuditLog.timestamp), desc(AuditLog.id)).first()
    prev_hash = latest_entry.hash if latest_entry else "0" * 64

    entry_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Serialize details to JSON string if provided as dict/object
    details_str = None
    if details is not None:
        if isinstance(details, str):
            details_str = details
        else:
            try:
                details_str = json.dumps(details, default=str)
            except Exception:
                details_str = str(details)

    # Compute SHA-256 hash
    hasher = hashlib.sha256()
    payload = (
        f"{prev_hash}|{entry_id}|{actor_user_id}|{action}|{resource_type}|"
        f"{resource_id}|{patient_id}|{now.isoformat()}|{details_str}"
    )
    hasher.update(payload.encode("utf-8"))
    entry_hash = hasher.hexdigest()

    audit_entry = AuditLog(
        id=entry_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        patient_id=patient_id,
        timestamp=now,
        details=details_str,
        prev_hash=prev_hash,
        hash=entry_hash,
    )

    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry
