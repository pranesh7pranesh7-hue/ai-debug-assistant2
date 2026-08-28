"""FastAPI Dependency Providers for Authentication, Database Sessions, and Configuration."""
from typing import Optional
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.exceptions import AuthError
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Extract and authenticate user from Authorization: Bearer <token> header."""
    if not authorization:
        raise AuthError(message="Missing Authorization header.")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError(message="Invalid Authorization header format. Expected 'Bearer <token>'.")

    token = parts[1]
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError(message="Token payload is missing subject identifier.")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise AuthError(message="User matching token credentials does not exist.")

    return user


def get_optional_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Extract user if valid token present, otherwise return None (for public / demo routes)."""
    if not authorization:
        return None
    try:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            payload = decode_access_token(parts[1])
            user_id = payload.get("sub")
            if user_id:
                return db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None
    return None
