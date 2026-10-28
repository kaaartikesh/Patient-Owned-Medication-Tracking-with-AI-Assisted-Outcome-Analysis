import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ConsentGrantRequest(BaseModel):
    doctor_id: uuid.UUID
    scope: str = "all"
    expires_at: Optional[datetime] = None


class ConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    scope: str
    granted_at: datetime
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    is_active: bool
    doctor_name: Optional[str] = None
    doctor_specialty: Optional[str] = None
    patient_name: Optional[str] = None
