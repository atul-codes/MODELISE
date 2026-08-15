"""
Auth primitives for Layer 2: PyJWT-based bearer tokens and Passlib/bcrypt
password hashing.

Layer 2 only needs a single administrative principal to gate the
admin/dashboard routes - there is deliberately no multi-tenant user
database here (the guardrail evaluate endpoint itself is intentionally
public per spec; see the README's Security Considerations section for why
that matters). The admin account is bootstrapped once at import time from
settings (ADMIN_USERNAME / ADMIN_PASSWORD, normally supplied via .env) and
its password is hashed immediately - the plaintext value never lives
anywhere after this module initializes. For a real multi-admin deployment,
replace `_ADMIN_DIRECTORY` with a proper user table.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=True)


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


_ADMIN_DIRECTORY: dict[str, dict[str, str]] = {
    settings.ADMIN_USERNAME: {
        "username": settings.ADMIN_USERNAME,
        "password_hash": hash_password(settings.ADMIN_PASSWORD),
    }
}


def get_admin(username: str) -> dict[str, str] | None:
    return _ADMIN_DIRECTORY.get(username)


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> tuple[str, int]:
    """Returns (encoded_jwt, expires_in_seconds)."""
    expire_minutes = expires_minutes or settings.JWT_EXPIRE_MINUTES
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "exp": expire_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expire_minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc


async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict[str, Any]:
    """FastAPI dependency that gates admin-only routes."""
    payload = decode_access_token(credentials.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return payload