from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Initializes the database engine using the connection string from your .env file.
# This is the actual bridge between your Python app and your PostgreSQL database.
engine = create_engine(settings.DATABASE_URL)

# Creates a factory for generating new database sessions.
# autocommit=False ensures we manually control when data is saved to prevent partial writes.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# The foundational class that all of Person 2's ORM models will inherit from.
# It tells SQLAlchemy that those classes should be translated into database tables.
Base = declarative_base()

# A FastAPI dependency that yields a single database session for a request, 
# and automatically closes it when the request is done. This prevents memory leaks.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()