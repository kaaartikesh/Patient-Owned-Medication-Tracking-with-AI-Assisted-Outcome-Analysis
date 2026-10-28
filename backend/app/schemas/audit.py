import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: Optional[uuid.UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    patient_id: Optional[uuid.UUID] = None
    timestamp: datetime
    details: Optional[str] = None
    prev_hash: Optional[str] = None
    hash: str
