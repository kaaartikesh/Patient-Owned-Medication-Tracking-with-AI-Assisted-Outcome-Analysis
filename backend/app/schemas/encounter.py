# backend/app/schemas/encounter.py
import uuid
from datetime import datetime
from pydantic import BaseModel
from app.models.encounter import EncounterStatus


class EncounterStartRequest(BaseModel):
    patient_id: uuid.UUID
    duration_minutes: int = 60


from typing import Optional


class EncounterResponse(BaseModel):
    id: uuid.UUID
    doctor_id: uuid.UUID
    patient_id: uuid.UUID
    status: EncounterStatus
    started_at: datetime
    expires_at: datetime
    doctor_name: Optional[str] = None
    patient_name: Optional[str] = None

    class Config:
        from_attributes = True