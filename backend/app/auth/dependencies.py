# backend/app/auth/dependencies.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.database import get_db
from app.models.user import User
from app.config import settings

# Tells FastAPI/Swagger where the frontend should POST credentials to get a token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# Extracts the JWT from the request, verifies it, and loads the matching User row
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # "sub" is the user's UUID (set in router.py's create_access_token call),
    # not an email — so we look up by id, not email
    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise credentials_exception

    return user

# ---------------------------------------------------------------------------
# Project context: this is the gateway every protected route depends on —
# any endpoint that needs "who is calling right now" (encounter creation,
# medication writes, consent checks) adds Depends(get_current_user) and
# gets a real User object back, or a 401 before it even runs. It decodes
# the JWT that router.py's /login issues, using the same JWT_SECRET from
# config.py, and resolves it against models/user.py's User table via the
# "sub" claim (user.id, not email — matches what create_access_token
# actually encodes).
# ---------------------------------------------------------------------------