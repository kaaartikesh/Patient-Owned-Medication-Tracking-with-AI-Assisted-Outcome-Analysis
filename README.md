# AegisMed: Patient-Owned Medication Tracking with AI-Assisted Outcome Analysis

> **EDI Project (Engineering Design & Innovation)**  
> **Course / Year:** Second Year Engineering  
> **Repository:** `kaaartikesh/Patient-Owned-Medication-Tracking-with-AI-Assisted-Outcome-Analysis`

---

## 🌟 Executive Summary & Problem Statement

In fragmented modern healthcare systems, patients consult multiple independent specialists (e.g. cardiologists, neurologists, general practitioners), each operating within isolated silos. This fragmentation leads to:

1. **Dangerous Multi-Doctor Drug Conflicts:** Adverse drug-drug interactions (e.g. Warfarin prescribed by a cardiologist reacting with Aspirin prescribed by another physician) that go undetected.
2. **Lack of Patient Data Sovereignty:** Patients have little control over who reads their health history or writes to their EHR.
3. **Loss of Real-World Outcome Telemetry:** Doctors rarely receive continuous feedback on medication efficacy and patient-observed side effects between clinical visits.
4. **Data Tampering & Vulnerability:** Centralized electronic health records can lack tamper-evident provenance and immutable audit trails.

**AegisMed** resolves these challenges by providing a **patient-sovereign medical tracking platform** combined with **cross-doctor drug safety checks**, **dynamic consent enforcement**, **clinical write sessions (Encounters)**, **patient outcome telemetry**, and **cryptographically chained audit logging (SHA-256)**.

---

## 🏗️ Architecture & Core Innovations

```
               ┌────────────────────────────────────────────────────────┐
               │              Patient-Owned Sovereign Hub               │
               │  • Grant / Revoke Consent    • Rate Efficacy & Side FX │
               │  • Approve / Reject Doctors  • Portable PDF/JSON Export│
               └───────────────────────────┬────────────────────────────┘
                                           │
                           REST API / JWT Authorization
                                           │
               ┌───────────────────────────▼────────────────────────────┐
               │                   FastAPI Core Backend                 │
               │                                                        │
               │   ┌────────────────────┐      ┌────────────────────┐   │
               │   │  Encounter Engine  │◄────►│  Drug Safety Check │   │
               │   │  (Active Windows)  │      │  (Cross-Physician) │   │
               │   └────────────────────┘      └────────────────────┘   │
               │                                                        │
               │   ┌────────────────────┐      ┌────────────────────┐   │
               │   │   Consent Engine   │◄────►│  Audit Hash Chain  │   │
               │   │  (Sovereign Access)│      │  (Tamper Evident)  │   │
               │   └────────────────────┘      └────────────────────┘   │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                   SQLite / PostgreSQL
```

### 1. Patient Data Sovereignty & Dynamic Consent
- **Granular Consent Records:** Access to patient medication records requires unrevoked, active consent granted explicitly by the patient.
- **Instant Revocation:** Patients can unilaterally revoke a doctor's access at any time, instantly invalidating the doctor's ability to view records or initiate write sessions.

### 2. Time-Bounded Clinical Encounters
- **Restricted Write Windows:** Doctors cannot write prescriptions or modify patient charts at will. Modifications must occur within a time-bounded **Clinical Encounter session** (e.g. 15, 30, or 60 minutes) authorized by active patient consent.

### 3. Cross-Doctor Drug Safety & Adverse Interaction Detection
- Prescribing a medication automatically runs a real-time safety evaluation against **all active prescriptions from all previous treating physicians and patient self-entries**.
- Flags high, medium, and low severity interactions (e.g. Warfarin ↔ Aspirin severe bleeding hazard) to alert doctors immediately before orders are finalized.

### 4. AI-Assisted Patient Outcome & Side-Effect Telemetry
- Patients log structured efficacy ratings (1–5 stars) and reported adverse reactions directly against specific medication entries.
- Provides treating physicians with longitudinal real-world telemetry to optimize treatment regimens.

### 5. Cryptographic Tamper-Evident Audit Logging
- Every sensitive action (`START_ENCOUNTER`, `ADD_MEDICATION`, `GRANT_CONSENT`, `REVOKE_CONSENT`, `EXPORT_HISTORY`, `READ_MEDICATIONS`) appends an immutable block to a **SHA-256 cryptographic hash chain** (`current_hash = SHA256(prev_hash + timestamp + actor + action + resource)`).
- Ensures data provenance and provides verifiable detection against database tampering.

### 6. Full EHR Data Portability
- Patients can export their complete unified medical history anytime in **machine-readable JSON** or **formatted clinical PDF reports** with one click.

---

## 🛠️ Technology Stack

### Backend
- **Framework:** FastAPI (Python 3.14 / 3.11+)
- **ORM / Database:** SQLAlchemy 2.0 with SQLite (development / testing) and PostgreSQL compatibility
- **Authentication:** OAuth2 with signed JWT tokens & bcrypt password hashing
- **Testing:** Pytest with in-memory static SQLite pool fixture architecture
- **PDF Generation:** ReportLab for structured clinical health summaries

### Frontend
- **Framework:** React 19 + Vite
- **Routing:** React Router v7 with protected role-based routing (`/patient-dashboard`, `/doctor-dashboard`)
- **Styling:** Modern Vanilla CSS design system with curated dark palette, glassmorphism, responsive cards, and micro-interactions
- **Icons:** Lucide React

---

## 🚀 Getting Started Locally

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Backend Setup
```bash
# Navigate to the backend directory
cd backend

# Activate virtual environment
# Windows:
..\.venv\Scripts\activate
# Linux/macOS:
source ../.venv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Run test suite
pytest tests -v

# Start FastAPI backend
uvicorn app.main:app --reload --port 8000
```
Backend will be live at `http://localhost:8000`. Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

### 2. Frontend Setup
```bash
# Navigate to the frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite dev server
npm run dev
```
Frontend will be live at `http://localhost:5173`.

---

## 🧪 Automated Test Suite

The test suite validates:
1. `test_health_check`: Backend liveness verification.
2. `test_register_user`: User registration with role attribution (Patient / Doctor).
3. `test_login_user`: JWT token generation and credential validation.
4. `test_consent_lifecycle_and_enforcement`: Rejection of unauthorized encounter starts without active consent; approval and revocation verification.
5. `test_interaction_checking_across_doctors`: Multi-doctor prescription conflict detection (Warfarin + Aspirin HIGH severity flag).
6. `test_effectiveness_logs`: Efficacy ratings and side-effect reporting with consent-gated clinical view.
7. `test_audit_log_hash_chaining`: Cryptographic SHA-256 block chain integrity verification across sequential events.
8. `test_export_json_and_pdf`: Verified machine-readable EHR export and binary PDF generation.

To run tests:
```bash
cd backend
pytest tests -v
```

---

## 📂 Project Directory Structure

```
patient-medication-system/
├── backend/
│   ├── app/
│   │   ├── audit/          # Cryptographic audit logging & hash chaining
│   │   ├── auth/           # OAuth2 JWT authentication & dependency injection
│   │   ├── consent/        # Patient consent granting, scoping, & revocation
│   │   ├── effectiveness/  # Patient-reported outcome & efficacy telemetry
│   │   ├── encounters/     # Time-bounded clinical encounter engine
│   │   ├── export/         # PDF (ReportLab) & JSON export services
│   │   ├── interactions/   # Drug-drug adverse interaction checking engine
│   │   ├── links/          # Doctor-patient linking & connection management
│   │   ├── medications/    # Unified cross-doctor medication entries
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic v2 validation & response schemas
│   │   ├── config.py       # Application settings & environment configuration
│   │   ├── database.py     # Database engine & sessionmaker
│   │   └── main.py         # FastAPI application entry point & router mounting
│   └── tests/
│       ├── conftest.py     # Shared test fixtures & in-memory test database
│       ├── test_auth.py    # Authentication test cases
│       └── test_group_a.py # Comprehensive integration & security test suite
├── frontend/
│   ├── public/             # Static assets & icons
│   ├── src/
│   │   ├── api/            # Complete HTTP API client for all backend routers
│   │   ├── components/     # Reusable components (Navbar, ProtectedRoute)
│   │   ├── context/        # AuthContext for session management & user profile hydration
│   │   ├── pages/          # Login, Register, PatientDashboard, DoctorDashboard
│   │   ├── App.jsx         # Role-based route definitions
│   │   ├── index.css       # Unified design system & custom CSS styling
│   │   └── main.jsx        # React application entry point
│   ├── index.html          # HTML entry point with Google Fonts
│   └── package.json        # Frontend dependencies & scripts
└── README.md               # Project documentation & architectural specification
```

---

## 🔒 Security & Privacy Features

- **Strict Role-Based Access Control (RBAC):** Verified at the route and dependency level.
- **Fail-Closed Encounter Logic:** Clinicians cannot prescribe or access records without unrevoked consent and an active encounter session.
- **Tamper-Evident Chaining:** SHA-256 parent hash verification prevents retrospective ledger alteration.
- **Data Portability:** Zero lock-in with one-click export for full patient autonomy.
