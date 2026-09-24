# backend/app/main.py

from fastapi import FastAPI

from app.database import Base, engine
from app.auth.router import router as auth_router

# Creates all tables (User, Patient, Doctor, etc.) that don't already exist.
# Fine for early development; swap for Alembic migrations once schemas stabilize.
Base.metadata.create_all(bind=engine)

# The single FastAPI application instance every router mounts onto
app = FastAPI(title="Patient Medication History System")

# Wires /auth/register and /auth/login into the app
app.include_router(auth_router)


# Simple liveness check to confirm the server is up
@app.get("/health")
def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Project context: this is the entry point that ties every teammate's file
# together — it imports Base/engine from database.py to build the schema
# from models/user.py, then mounts auth/router.py so /auth/register and
# /auth/login become real HTTP endpoints. Running this file (via
# uvicorn app.main:app --reload) is what actually starts the backend.
# Future routers (encounters, medications, consent, etc.) get added here
# the same way auth_router was: build the router, include_router() it.
# ---------------------------------------------------------------------------