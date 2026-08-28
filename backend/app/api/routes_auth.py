"""Authentication API Routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, ValidationError
from app.core.security import create_access_token, get_password_hash, verify_password
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    TokenResponse,
    UserLoginRequest,
    UserProfileResponse,
    UserRegisterRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user and return JWT access token."""
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise ValidationError(message="A user with this email address is already registered.")

    hashed_pw = get_password_hash(payload.password)
    new_user = User(
        email=payload.email.lower(),
        hashed_password=hashed_pw,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": str(new_user.id), "email": new_user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=new_user.id,
        email=new_user.email,
    )


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate user with email/password, update login status, and return JWT token."""
    from datetime import datetime
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise AuthError(message="Invalid email or password.")

    # Update login timestamp and online status
    user.last_login = datetime.utcnow()
    user.is_online = True
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
    )


@router.get("/me", response_model=UserProfileResponse)
def get_current_user_profile(user: User = Depends(get_current_user)):
    """Retrieve profile details of the authenticated user."""
    return user
