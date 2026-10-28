import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class InteractionFlagResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    medication_a_id: uuid.UUID
    medication_b_id: uuid.UUID
    medication_a_name: Optional[str] = None
    medication_b_name: Optional[str] = None
    severity: str
    description: str
    status: str
    created_at: datetime


class DrugInteractionCreate(BaseModel):
    drug_a: str
    drug_b: str
    severity: str
    description: str
