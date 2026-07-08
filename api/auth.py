"""
api/auth.py
───────────
JWT Authentication helpers for UPSC Test Series API.

Handles:
  - Password hashing (bcrypt via passlib)
  - JWT token creation and verification (python-jose)
  - FastAPI dependency: get_current_user  (inject into protected routes)
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from api.models import SessionLocal, User

# ── Configuration ────────────────────────────────────────────────────────────
# SECRET_KEY is read from the environment at runtime (after load_dotenv() in main.py).
# NEVER hardcode this in production — keep it in .env only.
def _secret_key() -> str:
    return os.getenv("SECRET_KEY", "fallback-insecure-key-set-SECRET_KEY-in-env")

ALGORITHM            = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24 * 7   # 7 days

import bcrypt

# ── OAuth2 scheme — reads "Authorization: Bearer <token>" from requests ──────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ── Database dependency ───────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Password helpers ──────────────────────────────────────────────────────────
def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt."""
    salt = bcrypt.gensalt()
    # truncate to 72 bytes to match bcrypt max length
    hashed = bcrypt.hashpw(plain[:72].encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain password matches stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain[:72].encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


# ── JWT helpers ───────────────────────────────────────────────────────────────
def create_access_token(user_id: int, email: str) -> str:
    """
    Create a signed JWT token embedding the user's ID and email.
    Token expires after TOKEN_EXPIRE_MINUTES.
    """
    payload = {
        "sub": str(user_id),       # subject = user id
        "email": email,
        "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),  # issued at
    }
    return jwt.encode(payload, _secret_key(), algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token.
    Returns the payload dict or None if invalid / expired.
    """
    try:
        return jwt.decode(token, _secret_key(), algorithms=[ALGORITHM])
    except JWTError:
        return None


# ── FastAPI Dependency: get_current_user ──────────────────────────────────────
def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to inject into any protected endpoint.
    Usage:
        @app.get("/protected")
        def protected(current_user: User = Depends(get_current_user)):
            ...

    Raises HTTP 401 if the token is missing, expired, or invalid.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated. Please log in.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Like get_current_user but returns None instead of raising 401.
    Use for endpoints that work for both anonymous and authenticated users.
    """
    if not token:
        return None
    payload = decode_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    return db.query(User).filter(User.id == int(user_id)).first()
