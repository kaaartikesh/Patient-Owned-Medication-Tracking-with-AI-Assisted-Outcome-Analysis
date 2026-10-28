import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.link import LinkStatus


class LinkRequest(BaseModel):
    patient_email: EmailStr


class LinkResponse(BaseModel):
    id: uuid.UUID
    doctor_id: uuid.UUID
    patient_id: uuid.UUID
    status: LinkStatus
    doctor_name: Optional[str] = None
    doctor_specialty: Optional[str] = None
    doctor_email: Optional[str] = None
    patient_name: Optional[str] = None
    patient_email: Optional[str] = None

    class Config:
        from_attributes = True