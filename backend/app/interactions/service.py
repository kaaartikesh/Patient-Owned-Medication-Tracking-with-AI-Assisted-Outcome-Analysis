import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.medication import MedicationEntry
from app.models.interaction import DrugInteraction, InteractionFlag
from app.interactions.seeds import seed_drug_interactions


def _clean_drug_name(name: str) -> str:
    """Normalize drug name by stripping strengths/units and non-alphanumeric chars."""
    cleaned = re.sub(r"\b\d+(\.\d+)?\s*(mg|mcg|g|ml|iu|tablets?|capsules?|drops?)\b", "", name, flags=re.IGNORECASE)
    cleaned = re.sub(r"[^a-zA-Z\s]", "", cleaned)
    return cleaned.strip().lower()


def find_interaction_rule(
    db: Session,
    med_name_1: str,
    med_name_2: str,
) -> Optional[DrugInteraction]:
    """
    Looks up known clinical drug interaction rules between two medication names.
    Supports exact matching and substring/token containment.
    """
    clean_1 = _clean_drug_name(med_name_1)
    clean_2 = _clean_drug_name(med_name_2)

    rules = db.query(DrugInteraction).all()
    for rule in rules:
        rule_a = rule.drug_a.lower().strip()
        rule_b = rule.drug_b.lower().strip()

        # Check (A matches clean_1 and B matches clean_2) OR (A matches clean_2 and B matches clean_1)
        matches_ab = (rule_a in clean_1 or clean_1 in rule_a) and (rule_b in clean_2 or clean_2 in rule_b)
        matches_ba = (rule_a in clean_2 or clean_2 in rule_a) and (rule_b in clean_1 or clean_1 in rule_b)

        if matches_ab or matches_ba:
            return rule

    return None


def check_and_create_interactions(
    db: Session,
    new_entry: MedicationEntry,
) -> List[InteractionFlag]:
    """
    Compares the newly added medication against other active medications for the patient.
    Specifically flags cross-doctor and patient-reported active medication conflicts.
    """
    # Ensure seed rules exist
    seed_drug_interactions(db)

    now = datetime.now(timezone.utc)

    # Query currently active medications for this patient
    active_meds = (
        db.query(MedicationEntry)
        .filter(
            MedicationEntry.patient_id == new_entry.patient_id,
            MedicationEntry.id != new_entry.id,
            MedicationEntry.is_active.is_(True),
            or_(MedicationEntry.end_date.is_(None), MedicationEntry.end_date > now),
        )
        .all()
    )

    created_flags: List[InteractionFlag] = []

    for existing_med in active_meds:
        # If new medication is added by a doctor, check against medications from other doctors or patient self-logs
        if new_entry.doctor_id and existing_med.doctor_id == new_entry.doctor_id:
            # If from same doctor during same prescription, can still check or prioritize cross-doctor
            pass

        rule = find_interaction_rule(db, new_entry.medication_name, existing_med.medication_name)
        if rule:
            # Check if this pair is already flagged
            existing_flag = (
                db.query(InteractionFlag)
                .filter(
                    InteractionFlag.patient_id == new_entry.patient_id,
                    or_(
                        and_(
                            InteractionFlag.medication_a_id == existing_med.id,
                            InteractionFlag.medication_b_id == new_entry.id,
                        ),
                        and_(
                            InteractionFlag.medication_a_id == new_entry.id,
                            InteractionFlag.medication_b_id == existing_med.id,
                        ),
                    ),
                )
                .first()
            )

            if not existing_flag:
                flag = InteractionFlag(
                    id=uuid.uuid4(),
                    patient_id=new_entry.patient_id,
                    medication_a_id=existing_med.id,
                    medication_b_id=new_entry.id,
                    severity=rule.severity,
                    description=f"{rule.severity} Interaction between {existing_med.medication_name} and {new_entry.medication_name}: {rule.description}",
                    status="FLAGGED",
                    created_at=now,
                )
                db.add(flag)
                created_flags.append(flag)

    if created_flags:
        db.commit()
        for flag in created_flags:
            db.refresh(flag)

    return created_flags
