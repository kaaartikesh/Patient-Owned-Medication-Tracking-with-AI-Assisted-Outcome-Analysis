import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DrugInteraction(Base):
    __tablename__ = "drug_interactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    drug_a: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    drug_b: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)  # CRITICAL, HIGH, MODERATE, LOW
    description: Mapped[str] = mapped_column(Text, nullable=False)


class InteractionFlag(Base):
    __tablename__ = "interaction_flags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medication_a_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medication_entries.id", ondelete="CASCADE"), nullable=False
    )
    medication_b_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medication_entries.id", ondelete="CASCADE"), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="FLAGGED", nullable=False)  # FLAGGED, ACKNOWLEDGED, RESOLVED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    medication_a: Mapped["MedicationEntry"] = relationship(
        "MedicationEntry", foreign_keys=[medication_a_id]
    )
    medication_b: Mapped["MedicationEntry"] = relationship(
        "MedicationEntry", foreign_keys=[medication_b_id]
    )
