import uuid
from datetime import datetime, timedelta, timezone
import pytest
from jose import jwt

from app.models.user import User, Patient, Doctor, UserRole
from app.models.link import DoctorPatientLink, LinkStatus
from app.models.encounter import Encounter, EncounterStatus
from app.models.medication import MedicationEntry
from app.models.consent import ConsentRecord
from app.auth.security import create_access_token
from app.config import settings

from tests.conftest import client, TestingSessionLocal


def setup_test_users():
    db = TestingSessionLocal()

    p1_user_id = uuid.uuid4()
    patient1_id = uuid.uuid4()
    p2_user_id = uuid.uuid4()
    patient2_id = uuid.uuid4()

    d1_user_id = uuid.uuid4()
    doctor1_id = uuid.uuid4()
    d2_user_id = uuid.uuid4()
    doctor2_id = uuid.uuid4()

    # Patient 1
    p1_user = User(
        id=p1_user_id,
        email=f"patient1_{uuid.uuid4().hex[:6]}@hospital.com",
        hashed_password="fakehashpassword123",
        role=UserRole.PATIENT,
    )
    db.add(p1_user)
    patient1 = Patient(id=patient1_id, user_id=p1_user_id, full_name="Patient One")
    db.add(patient1)

    # Patient 2
    p2_user = User(
        id=p2_user_id,
        email=f"patient2_{uuid.uuid4().hex[:6]}@hospital.com",
        hashed_password="fakehashpassword123",
        role=UserRole.PATIENT,
    )
    db.add(p2_user)
    patient2 = Patient(id=patient2_id, user_id=p2_user_id, full_name="Patient Two")
    db.add(patient2)

    # Doctor 1
    d1_user = User(
        id=d1_user_id,
        email=f"doctor1_{uuid.uuid4().hex[:6]}@hospital.com",
        hashed_password="fakehashpassword123",
        role=UserRole.DOCTOR,
    )
    db.add(d1_user)
    doctor1 = Doctor(id=doctor1_id, user_id=d1_user_id, full_name="Dr. Doctor One")
    db.add(doctor1)

    # Doctor 2
    d2_user = User(
        id=d2_user_id,
        email=f"doctor2_{uuid.uuid4().hex[:6]}@hospital.com",
        hashed_password="fakehashpassword123",
        role=UserRole.DOCTOR,
    )
    db.add(d2_user)
    doctor2 = Doctor(id=doctor2_id, user_id=d2_user_id, full_name="Dr. Doctor Two")
    db.add(doctor2)

    db.commit()
    db.close()

    p1_token = create_access_token(data={"sub": str(p1_user_id), "role": "patient", "name": "Patient One"})
    p2_token = create_access_token(data={"sub": str(p2_user_id), "role": "patient", "name": "Patient Two"})
    d1_token = create_access_token(data={"sub": str(d1_user_id), "role": "doctor", "name": "Dr. Doctor One"})
    d2_token = create_access_token(data={"sub": str(d2_user_id), "role": "doctor", "name": "Dr. Doctor Two"})

    return {
        "p1_user_id": p1_user_id,
        "patient1_id": patient1_id,
        "p1_token": p1_token,
        "p2_user_id": p2_user_id,
        "patient2_id": patient2_id,
        "p2_token": p2_token,
        "d1_user_id": d1_user_id,
        "doctor1_id": doctor1_id,
        "d1_token": d1_token,
        "d2_user_id": d2_user_id,
        "doctor2_id": doctor2_id,
        "d2_token": d2_token,
    }


def test_expired_encounter_prescribe_returns_403():
    data = setup_test_users()
    db = TestingSessionLocal()

    # Link Doctor 1 and Patient 1
    link = DoctorPatientLink(doctor_id=data["doctor1_id"], patient_id=data["patient1_id"], status=LinkStatus.ACTIVE)
    db.add(link)
    consent = ConsentRecord(doctor_id=data["doctor1_id"], patient_id=data["patient1_id"], scope="all")
    db.add(consent)

    # Encounter with expires_at directly set in the past
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    enc = Encounter(
        doctor_id=data["doctor1_id"],
        patient_id=data["patient1_id"],
        started_at=past_time - timedelta(minutes=15),
        expires_at=past_time,
        status=EncounterStatus.ACTIVE,
    )
    db.add(enc)
    db.commit()
    enc_id = enc.id
    db.close()

    d1_headers = {"Authorization": f"Bearer {data['d1_token']}"}
    res = client.post(
        "/medications",
        json={
            "patient_id": str(data["patient1_id"]),
            "encounter_id": str(enc_id),
            "medication_name": "Amoxicillin",
            "dosage": "500mg",
        },
        headers=d1_headers,
    )
    assert res.status_code == 403, f"Expected 403 for expired encounter, got {res.status_code}: {res.text}"


def test_closed_encounter_prescribe_returns_403():
    data = setup_test_users()
    db = TestingSessionLocal()

    link = DoctorPatientLink(doctor_id=data["doctor1_id"], patient_id=data["patient1_id"], status=LinkStatus.ACTIVE)
    db.add(link)
    consent = ConsentRecord(doctor_id=data["doctor1_id"], patient_id=data["patient1_id"], scope="all")
    db.add(consent)

    future_time = datetime.now(timezone.utc) + timedelta(minutes=30)
    enc = Encounter(
        doctor_id=data["doctor1_id"],
        patient_id=data["patient1_id"],
        started_at=datetime.now(timezone.utc),
        expires_at=future_time,
        status=EncounterStatus.CLOSED,
    )
    db.add(enc)
    db.commit()
    enc_id = enc.id
    db.close()

    d1_headers = {"Authorization": f"Bearer {data['d1_token']}"}
    res = client.post(
        "/medications",
        json={
            "patient_id": str(data["patient1_id"]),
            "encounter_id": str(enc_id),
            "medication_name": "Amoxicillin",
            "dosage": "500mg",
        },
        headers=d1_headers,
    )
    assert res.status_code == 403, f"Expected 403 for closed encounter, got {res.status_code}: {res.text}"


def test_consent_revoked_start_encounter_and_read_medications_return_403():
    data = setup_test_users()
    db = TestingSessionLocal()

    link = DoctorPatientLink(doctor_id=data["doctor1_id"], patient_id=data["patient1_id"], status=LinkStatus.ACTIVE)
    db.add(link)
    consent = ConsentRecord(
        doctor_id=data["doctor1_id"],
        patient_id=data["patient1_id"],
        scope="all",
        revoked_at=datetime.now(timezone.utc),
    )
    db.add(consent)
    db.commit()
    db.close()

    d1_headers = {"Authorization": f"Bearer {data['d1_token']}"}

    # Start encounter
    res1 = client.post(
        "/encounters/start",
        json={"patient_id": str(data["patient1_id"]), "duration_minutes": 30},
        headers=d1_headers,
    )
    assert res1.status_code == 403, f"Expected 403 for encounters/start with revoked consent, got {res1.status_code}"

    # Read medications
    res2 = client.get(
        f"/medications/{data['patient1_id']}",
        headers=d1_headers,
    )
    assert res2.status_code == 403, f"Expected 403 for medications read with revoked consent, got {res2.status_code}"


def test_link_revoked_start_encounter_and_read_medications_return_403():
    data = setup_test_users()
    db = TestingSessionLocal()

    link = DoctorPatientLink(doctor_id=data["doctor1_id"], patient_id=data["patient1_id"], status=LinkStatus.REVOKED)
    db.add(link)
    consent = ConsentRecord(doctor_id=data["doctor1_id"], patient_id=data["patient1_id"], scope="all")
    db.add(consent)
    db.commit()
    db.close()

    d1_headers = {"Authorization": f"Bearer {data['d1_token']}"}

    # Start encounter
    res1 = client.post(
        "/encounters/start",
        json={"patient_id": str(data["patient1_id"]), "duration_minutes": 30},
        headers=d1_headers,
    )
    assert res1.status_code == 403, f"Expected 403 for encounters/start with revoked link, got {res1.status_code}"

    # Read medications
    res2 = client.get(
        f"/medications/{data['patient1_id']}",
        headers=d1_headers,
    )
    assert res2.status_code == 403, f"Expected 403 for medications read with revoked link, got {res2.status_code}"


def test_never_linked_doctor_patient_data_endpoints_return_403():
    data = setup_test_users()
    # Doctor 1 has NO link to Patient 1
    d1_headers = {"Authorization": f"Bearer {data['d1_token']}"}
    p1_id = data["patient1_id"]

    # medications
    res_meds = client.get(f"/medications/{p1_id}", headers=d1_headers)
    assert res_meds.status_code == 403, f"Expected 403 for unlinked doctor GET /medications, got {res_meds.status_code}"

    # interactions
    res_inter = client.get(f"/interactions/{p1_id}", headers=d1_headers)
    assert res_inter.status_code == 403, f"Expected 403 for unlinked doctor GET /interactions, got {res_inter.status_code}"

    # effectiveness
    res_eff = client.get(f"/effectiveness/patient/{p1_id}", headers=d1_headers)
    assert res_eff.status_code == 403, f"Expected 403 for unlinked doctor GET /effectiveness, got {res_eff.status_code}"

    # audit
    res_audit = client.get(f"/audit/{p1_id}", headers=d1_headers)
    assert res_audit.status_code == 403, f"Expected 403 for unlinked doctor GET /audit, got {res_audit.status_code}"

    # export
    res_export = client.get(f"/export/{p1_id}", headers=d1_headers)
    assert res_export.status_code == 403, f"Expected 403 for unlinked doctor GET /export, got {res_export.status_code}"


def test_patient_a_requesting_patient_b_data_returns_403():
    data = setup_test_users()
    # Patient 1 requesting Patient 2's data
    p1_headers = {"Authorization": f"Bearer {data['p1_token']}"}
    p2_id = data["patient2_id"]

    # medications
    res_meds = client.get(f"/medications/{p2_id}", headers=p1_headers)
    assert res_meds.status_code == 403, f"Expected 403 for patient A GET /medications/patient_b, got {res_meds.status_code}"

    # interactions
    res_inter = client.get(f"/interactions/{p2_id}", headers=p1_headers)
    assert res_inter.status_code == 403, f"Expected 403 for patient A GET /interactions/patient_b, got {res_inter.status_code}"

    # effectiveness
    res_eff = client.get(f"/effectiveness/patient/{p2_id}", headers=p1_headers)
    assert res_eff.status_code == 403, f"Expected 403 for patient A GET /effectiveness/patient_b, got {res_eff.status_code}"

    # audit
    res_audit = client.get(f"/audit/{p2_id}", headers=p1_headers)
    assert res_audit.status_code == 403, f"Expected 403 for patient A GET /audit/patient_b, got {res_audit.status_code}"

    # export
    res_export = client.get(f"/export/{p2_id}", headers=p1_headers)
    assert res_export.status_code == 403, f"Expected 403 for patient A GET /export/patient_b, got {res_export.status_code}"


def test_disconnect_then_relink_old_consent_not_reactivated():
    data = setup_test_users()
    db = TestingSessionLocal()

    # Initial link & active consent
    link = DoctorPatientLink(doctor_id=data["doctor1_id"], patient_id=data["patient1_id"], status=LinkStatus.ACTIVE)
    db.add(link)
    consent = ConsentRecord(doctor_id=data["doctor1_id"], patient_id=data["patient1_id"], scope="all")
    db.add(consent)
    db.commit()
    link_id = link.id
    db.close()

    p1_headers = {"Authorization": f"Bearer {data['p1_token']}"}
    d1_headers = {"Authorization": f"Bearer {data['d1_token']}"}

    # Step 1: Disconnect / reject link
    reject_res = client.post(f"/links/{link_id}/reject", headers=p1_headers)
    assert reject_res.status_code == 200, f"Expected 200 on link reject, got {reject_res.status_code}"

    # Step 2: Doctor re-requests link
    # Patient email lookup
    db = TestingSessionLocal()
    p1_user = db.query(User).filter(User.id == data["p1_user_id"]).first()
    p1_email = p1_user.email
    db.close()

    req_res = client.post("/links/request", json={"patient_email": p1_email}, headers=d1_headers)
    assert req_res.status_code == 201 or req_res.status_code == 200, f"Expected 200/201 on link request, got {req_res.status_code}"
    new_link_id = req_res.json()["id"]

    # Step 3: Patient approves relink
    appr_res = client.post(f"/links/{new_link_id}/approve", headers=p1_headers)
    assert appr_res.status_code == 200, f"Expected 200 on link approve, got {appr_res.status_code}"

    # Step 4: Doctor attempts to start encounter WITHOUT newly granted consent
    # The old consent must NOT be active!
    enc_res = client.post(
        "/encounters/start",
        json={"patient_id": str(data["patient1_id"]), "duration_minutes": 30},
        headers=d1_headers,
    )
    assert enc_res.status_code == 403, (
        f"Old consent silently reactivated after relink! Expected 403, got {enc_res.status_code}: {enc_res.text}"
    )


def test_prescribing_with_mismatched_encounter_rejected():
    data = setup_test_users()
    db = TestingSessionLocal()

    # Link Doctor 1 with Patient 1
    l1 = DoctorPatientLink(doctor_id=data["doctor1_id"], patient_id=data["patient1_id"], status=LinkStatus.ACTIVE)
    db.add(l1)
    # Link Doctor 2 with Patient 2
    l2 = DoctorPatientLink(doctor_id=data["doctor2_id"], patient_id=data["patient2_id"], status=LinkStatus.ACTIVE)
    db.add(l2)

    c1 = ConsentRecord(doctor_id=data["doctor1_id"], patient_id=data["patient1_id"], scope="all")
    db.add(c1)
    c2 = ConsentRecord(doctor_id=data["doctor2_id"], patient_id=data["patient2_id"], scope="all")
    db.add(c2)

    future_time = datetime.now(timezone.utc) + timedelta(minutes=30)
    # Doctor 1's encounter with Patient 1
    enc1 = Encounter(
        doctor_id=data["doctor1_id"],
        patient_id=data["patient1_id"],
        started_at=datetime.now(timezone.utc),
        expires_at=future_time,
        status=EncounterStatus.ACTIVE,
    )
    db.add(enc1)

    # Doctor 2's encounter with Patient 2
    enc2 = Encounter(
        doctor_id=data["doctor2_id"],
        patient_id=data["patient2_id"],
        started_at=datetime.now(timezone.utc),
        expires_at=future_time,
        status=EncounterStatus.ACTIVE,
    )
    db.add(enc2)
    db.commit()

    enc1_id = enc1.id
    enc2_id = enc2.id
    db.close()

    d1_headers = {"Authorization": f"Bearer {data['d1_token']}"}

    # Case A: Doctor 1 tries to prescribe for Patient 1 using Doctor 2's encounter (different doctor)
    res_a = client.post(
        "/medications",
        json={
            "patient_id": str(data["patient1_id"]),
            "encounter_id": str(enc2_id),
            "medication_name": "Lisinopril",
            "dosage": "10mg",
        },
        headers=d1_headers,
    )
    assert res_a.status_code in [400, 403, 404], (
        f"Prescribing with another doctor's encounter should be rejected, got {res_a.status_code}"
    )

    # Case B: Doctor 1 tries to prescribe for Patient 2 using encounter for Patient 1 (different patient)
    res_b = client.post(
        "/medications",
        json={
            "patient_id": str(data["patient2_id"]),
            "encounter_id": str(enc1_id),
            "medication_name": "Lisinopril",
            "dosage": "10mg",
        },
        headers=d1_headers,
    )
    assert res_b.status_code in [400, 403, 404], (
        f"Prescribing for another patient using mismatched encounter should be rejected, got {res_b.status_code}"
    )


def test_expired_and_tampered_tokens_return_401():
    data = setup_test_users()

    # 1. Expired token
    expired_payload = {
        "sub": str(data["p1_user_id"]),
        "role": "patient",
        "name": "Patient One",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    # 2. Tampered token
    valid_token = data["p1_token"]
    tampered_token = valid_token[:-6] + "xxxxxx"

    p1_id = data["patient1_id"]
    test_endpoints = [
        ("GET", f"/medications/{p1_id}"),
        ("GET", "/links/my"),
        ("GET", f"/audit/{p1_id}"),
        ("GET", f"/interactions/{p1_id}"),
        ("GET", f"/effectiveness/patient/{p1_id}"),
        ("GET", f"/export/{p1_id}"),
    ]

    for method, path in test_endpoints:
        # Expired token test
        exp_res = client.request(method, path, headers={"Authorization": f"Bearer {expired_token}"})
        assert exp_res.status_code == 401, f"Expected 401 for expired token on {method} {path}, got {exp_res.status_code}"

        # Tampered token test
        tamp_res = client.request(method, path, headers={"Authorization": f"Bearer {tampered_token}"})
        assert tamp_res.status_code == 401, f"Expected 401 for tampered token on {method} {path}, got {tamp_res.status_code}"


def test_jwt_secret_validation_refuses_placeholder_and_short_values():
    from app.config import Settings
    from pydantic import ValidationError

    # Test 1: Placeholder value must raise ValidationError
    with pytest.raises(ValidationError) as exc1:
        Settings(
            DATABASE_URL="sqlite:///:memory:",
            JWT_SECRET="change-this-to-something-random-and-long-later",
            JWT_ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=60,
        )
    assert "placeholder" in str(exc1.value).lower()

    # Test 2: Shorter than 32 characters must raise ValidationError
    with pytest.raises(ValidationError) as exc2:
        Settings(
            DATABASE_URL="sqlite:///:memory:",
            JWT_SECRET="short-secret-under-32-chars",
            JWT_ALGORITHM="HS256",
            ACCESS_TOKEN_EXPIRE_MINUTES=60,
        )
    assert "32 characters" in str(exc2.value).lower()

    # Test 3: Valid 32+ char secret succeeds
    valid_settings = Settings(
        DATABASE_URL="sqlite:///:memory:",
        JWT_SECRET="this-is-a-valid-secure-key-exceeding-thirty-two-chars!",
        JWT_ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=60,
    )
    assert valid_settings.JWT_SECRET == "this-is-a-valid-secure-key-exceeding-thirty-two-chars!"

