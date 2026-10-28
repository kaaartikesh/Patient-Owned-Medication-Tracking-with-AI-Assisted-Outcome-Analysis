from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.auth.router import router as auth_router
from app.links.router import router as links_router
from app.encounters.router import router as encounters_router
from app.medications.router import router as medications_router
from app.consent.router import router as consent_router
from app.audit.router import router as audit_router
from app.interactions.router import router as interactions_router
from app.effectiveness.router import router as effectiveness_router
from app.export.router import router as export_router

# Import all models so Base.metadata.create_all registers every table
from app.models import (  # noqa: F401
    user,
    link,
    encounter,
    medication,
    audit,
    consent,
    interaction,
    effectiveness,
)

app = FastAPI(title="Patient Medication History System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database schema is managed via Alembic migrations (Base.metadata.create_all removed)

# Register all feature routers
app.include_router(auth_router)
app.include_router(links_router)
app.include_router(encounters_router)
app.include_router(medications_router)
app.include_router(consent_router)
app.include_router(audit_router)
app.include_router(interactions_router)
app.include_router(effectiveness_router)
app.include_router(export_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}