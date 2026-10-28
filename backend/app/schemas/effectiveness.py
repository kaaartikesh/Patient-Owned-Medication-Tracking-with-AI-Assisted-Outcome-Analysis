import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class EffectivenessCreateRequest(BaseModel):
    medication_entry_id: uuid.UUID
    rating: int = Field(..., ge=1, le=5, description="Effectiveness score from 1 (ineffective) to 5 (highly effective)")
    side_effects: Optional[str] = None


class EffectivenessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    medication_entry_id: uuid.UUID
    patient_id: uuid.UUID
    medication_name: Optional[str] = None
    rating: int
    side_effects: Optional[str] = None
    logged_at: datetime
