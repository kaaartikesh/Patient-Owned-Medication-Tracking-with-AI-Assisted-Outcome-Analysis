import uuid
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models.user import User, Patient, Doctor, UserRole
from app.models.link import DoctorPatientLink, LinkStatus
from app.models.encounter import Encounter, EncounterStatus
from app.models.medication import MedicationEntry
from app.models.consent import ConsentRecord
from app.models.audit import AuditLog
from app.models.interaction import DrugInteraction, InteractionFlag
from app.models.effectiveness import EffectivenessLog
from app.auth.security import create_access_token

from tests.conftest import client, TestingSessionLocal


def create_test_patient_and_doctor():
    db = TestingSessionLocal()

    p_user_id = uuid.uuid4()
    patient_id = uuid.uuid4()
    d1_user_id = uuid.uuid4()
    doctor1_id = uuid.uuid4()
    d2_user_id = uuid.uuid4()
    doctor2_id = uuid.uuid4()

    # Patient
    p_user = User(
        id=p_user_id,
        email=f"patient_{uuid.uuid4().hex[:6]}@hospital.com",
        hashed_password="fakehashpassword123",
        role=UserRole.PATIENT,
    )
    db.add(p_user)
    patient = Patient(id=patient_id, user_id=p_user_id, full_name="Alice Patient")
    db.add(patient)

    # Doctor 1
    d1_user = User(
        id=d1_user_id,
        email=f"doctor1_{uuid.uuid4().hex[:6]}@hospital.com",
        hashed_password="fakehashpassword123",
        role=UserRole.DOCTOR,
    )
    db.add(d1_user)
    doctor1 = Doctor(id=doctor1_id, user_id=d1_user_id, full_name="Dr. Bob Cardiologist")
    db.add(doctor1)

    # Doctor 2
    d2_user = User(
        id=d2_user_id,
        email=f"doctor2_{uuid.uuid4().hex[:6]}@hospital.com",
        hashed_password="fakehashpassword123",
        role=UserRole.DOCTOR,
    )
    db.add(d2_user)
    doctor2 = Doctor(id=doctor2_id, user_id=d2_user_id, full_name="Dr. Charlie Neurologist")
    db.add(doctor2)

    db.commit()
    db.close()

    p_token = create_access_token(data={"sub": str(p_user_id), "role": "patient", "name": "Alice Patient"})
    d1_token = create_access_token(data={"sub": str(d1_user_id), "role": "doctor", "name": "Dr. Bob"})
    d2_token = create_access_token(data={"sub": str(d2_user_id), "role": "doctor", "name": "Dr. Charlie"})

    return {
        "p_user_id": p_user_id,
        "patient_id": patient_id,
        "p_token": p_token,
        "d1_user_id": d1_user_id,
        "doctor1_id": doctor1_id,
        "d1_token": d1_token,
        "d2_user_id": d2_user_id,
        "doctor2_id": doctor2_id,
        "d2_token": d2_token,
    }


def test_consent_lifecycle_and_enforcement():
    data = create_test_patient_and_doctor()
    p_headers = {"Authorization": f"Bearer {data['p_token']}"}
    d1_headers = {"Authorization": f"Bearer {data['d1_token']}"}

    db = TestingSessionLocal()
    # Establish active doctor-patient link
    link = DoctorPatientLink(
        doctor_id=data["doctor1_id"],
        patient_id=data["patient_id"],
        status=LinkStatus.ACTIVE,
    )
    db.add(link)
    db.commit()
    db.close()

    # 1. Doctor tries to start encounter without consent -> 403
    start_resp = client.post(
        "/encounters/start",
        json={"patient_id": str(data["patient_id"]), "duration_minutes": 30},
        headers=d1_headers,
    )
    assert start_resp.status_code == 403
    assert "No active consent" in start_resp.json()["detail"]

    # 2. Patient grants consent to Doctor 1
    grant_resp = client.post(
        "/consent/grant",
        json={"doctor_id": str(data["doctor1_id"]), "scope": "all"},
        headers=p_headers,
    )
    assert grant_resp.status_code == 201
    consent_id = grant_resp.json()["id"]
    assert grant_resp.json()["is_active"] is True

    # 3. Doctor starts encounter with active consent -> 201 Success
    start_resp_2 = client.post(
        "/encounters/start",
        json={"patient_id": str(data["patient_id"]), "duration_minutes": 30},
        headers=d1_headers,
    )
    assert start_resp_2.status_code == 201

    # 4. Patient revokes consent
    revoke_resp = client.post(f"/consent/{consent_id}/revoke", headers=p_headers)
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["revoked_at"] is not None

    # 5. Doctor tries to start another encounter after consent revoked -> 403
    start_resp_3 = client.post(
        "/encounters/start",
        json={"patient_id": str(data["patient_id"]), "duration_minutes": 30},
        headers=d1_headers,
    )
    assert start_resp_3.status_code == 403


def test_interaction_checking_across_doctors():
    data = create_test_patient_and_doctor()
    p_headers = {"Authorization": f"Bearer {data['p_token']}"}
    d1_headers = {"Authorization": f"Bearer {data['d1_token']}"}
    d2_headers = {"Authorization": f"Bearer {data['d2_token']}"}

    db = TestingSessionLocal()
    # Activate links & consent for both doctors
    l1 = DoctorPatientLink(doctor_id=data["doctor1_id"], patient_id=data["patient_id"], status=LinkStatus.ACTIVE)
    l2 = DoctorPatientLink(doctor_id=data["doctor2_id"], patient_id=data["patient_id"], status=LinkStatus.ACTIVE)
    c1 = ConsentRecord(doctor_id=data["doctor1_id"], patient_id=data["patient_id"], scope="all")
    c2 = ConsentRecord(doctor_id=data["doctor2_id"], patient_id=data["patient_id"], scope="all")
    db.add_all([l1, l2, c1, c2])
    db.commit()
    db.close()

    # Start encounters for both doctors
    enc1 = client.post("/encounters/start", json={"patient_id": str(data["patient_id"]), "duration_minutes": 60}, headers=d1_headers).json()
    enc2 = client.post("/encounters/start", json={"patient_id": str(data["patient_id"]), "duration_minutes": 60}, headers=d2_headers).json()

    # Doctor 1 prescribes Warfarin
    med1_resp = client.post(
        "/medications",
        json={
            "patient_id": str(data["patient_id"]),
            "encounter_id": enc1["id"],
            "medication_name": "Warfarin 5mg",
            "dosage": "5mg",
            "frequency": "Daily",
            "is_active": True,
        },
        headers=d1_headers,
    )
    assert med1_resp.status_code == 201
    assert len(med1_resp.json()["interaction_flags"]) == 0

    # Doctor 2 prescribes Aspirin (Known HIGH severity interaction with Warfarin)
    med2_resp = client.post(
        "/medications",
        json={
            "patient_id": str(data["patient_id"]),
            "encounter_id": enc2["id"],
            "medication_name": "Aspirin 81mg",
            "dosage": "81mg",
            "frequency": "Daily",
            "is_active": True,
        },
        headers=d2_headers,
    )
    assert med2_resp.status_code == 201
    flags = med2_resp.json()["interaction_flags"]
    assert len(flags) > 0
    assert flags[0]["severity"] == "HIGH"
    assert "Warfarin" in flags[0]["description"]

    # Verify GET /interactions/{patient_id}
    inter_resp = client.get(f"/interactions/{data['patient_id']}", headers=p_headers)
    assert inter_resp.status_code == 200
    assert len(inter_resp.json()) >= 1


def test_effectiveness_logs():
    data = create_test_patient_and_doctor()
    p_headers = {"Authorization": f"Bearer {data['p_token']}"}
    d1_headers = {"Authorization": f"Bearer {data['d1_token']}"}

    # Patient logs self-medication
    med_resp = client.post(
        "/medications",
        json={
            "patient_id": str(data["patient_id"]),
            "medication_name": "Metformin 500mg",
            "dosage": "500mg",
            "frequency": "Twice daily",
        },
        headers=p_headers,
    )
    assert med_resp.status_code == 201
    med_id = med_resp.json()["id"]

    # Patient logs effectiveness rating (4/5) and side effects
    eff_resp = client.post(
        "/effectiveness",
        json={
            "medication_entry_id": med_id,
            "rating": 4,
            "side_effects": "Mild nausea initially, subsided after 3 days.",
        },
        headers=p_headers,
    )
    assert eff_resp.status_code == 201
    assert eff_resp.json()["rating"] == 4
    assert eff_resp.json()["medication_name"] == "Metformin 500mg"

    # Doctor without consent cannot read -> 403
    doc_read = client.get(f"/effectiveness/patient/{data['patient_id']}", headers=d1_headers)
    assert doc_read.status_code == 403

    # Add active link and consent
    db = TestingSessionLocal()
    link = DoctorPatientLink(doctor_id=data["doctor1_id"], patient_id=data["patient_id"], status=LinkStatus.ACTIVE)
    consent = ConsentRecord(doctor_id=data["doctor1_id"], patient_id=data["patient_id"], scope="all")
    db.add_all([link, consent])
    db.commit()
    db.close()

    # Consented doctor reads effectiveness logs -> 200
    doc_read_2 = client.get(f"/effectiveness/patient/{data['patient_id']}", headers=d1_headers)
    assert doc_read_2.status_code == 200
    assert len(doc_read_2.json()) >= 1
    assert doc_read_2.json()[0]["rating"] == 4


def test_audit_log_hash_chaining():
    db = TestingSessionLocal()
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.asc()).all()
    assert len(logs) > 0

    # Verify cryptographic hash chain integrity
    for i in range(1, len(logs)):
        assert logs[i].prev_hash == logs[i - 1].hash
    db.close()


def test_export_json_and_pdf():
    data = create_test_patient_and_doctor()
    p_headers = {"Authorization": f"Bearer {data['p_token']}"}

    # Add a medication for export
    client.post(
        "/medications",
        json={"patient_id": str(data["patient_id"]), "medication_name": "Amoxicillin 500mg"},
        headers=p_headers,
    )

    # 1. Export JSON
    json_resp = client.get(f"/export/{data['patient_id']}?format=json", headers=p_headers)
    assert json_resp.status_code == 200
    body = json_resp.json()
    assert "medications" in body
    assert "encounters" in body
    assert "effectiveness_logs" in body
    assert "interaction_flags" in body

    # 2. Export PDF
    pdf_resp = client.get(f"/export/{data['patient_id']}?format=pdf", headers=p_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")
