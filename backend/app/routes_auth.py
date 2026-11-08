from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.schemas import Credentials, TokenResponse
from app.security import hash_password, issue_token, verify_password
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token(user: User) -> TokenResponse:
    return TokenResponse(access_token=issue_token(user), expires_in=settings.access_token_minutes * 60, email=user.email)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: Credentials, db: Session = Depends(get_db)):
    email = str(payload.email).casefold()
    exists = db.scalar(select(User.id).where(User.email == email))
    if exists:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: Credentials, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(payload.email).casefold()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password", headers={"WWW-Authenticate": "Bearer"})
    return _token(user)

