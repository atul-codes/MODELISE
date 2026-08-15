"""
Auth (JWT + bcrypt, same bootstrapped-single-admin pattern used across
guardrail_layer2 and geo_policy_engine) plus symmetric encryption for
secrets that get stored at rest: commercial AI provider API keys, and any
auth header value a custom model endpoint needs.

Encryption uses Fernet (AES-128-CBC + HMAC, from the `cryptography`
package) rather than something home-rolled. Fernet tokens are
self-describing and include a timestamp + HMAC, so a tampered or
corrupted ciphertext fails loudly (InvalidToken) instead of decrypting
into garbage silently.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from src.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=True)

_ADMIN_DIRECTORY: dict[str, dict[str, str]] = {
    settings.ADMIN_USERNAME: {
        "username": settings.ADMIN_USERNAME,
        "password_hash": pwd_context.hash(settings.ADMIN_PASSWORD),
    }
}


def get_admin(username: str) -> dict[str, str] | None:
    return _ADMIN_DIRECTORY.get(username)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: str) -> tuple[str, int]:
    expire_minutes = settings.JWT_EXPIRE_MINUTES
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "role": role, "exp": expire_at, "iat": datetime.now(timezone.utc)}
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expire_minutes * 60


async def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict[str, Any]:
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return payload


# ---------------------------------------------------------------------------
# Credential-at-rest encryption
# ---------------------------------------------------------------------------
class CredentialCipherNotConfigured(RuntimeError):
    pass


def _get_cipher() -> Fernet:
    key = settings.CREDENTIAL_ENCRYPTION_KEY
    if not key:
        raise CredentialCipherNotConfigured(
            "CREDENTIAL_ENCRYPTION_KEY is not set. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
            "and put it in .env before storing any commercial AI keys or custom-endpoint secrets."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_secret(plaintext: str) -> str:
    return _get_cipher().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _get_cipher().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored credential could not be decrypted - CREDENTIAL_ENCRYPTION_KEY may have changed.",
        ) from exc


def mask_secret(plaintext: str, visible_suffix: int = 4) -> str:
    """For display in the GUI only - never send full stored keys back to the frontend."""
    if len(plaintext) <= visible_suffix:
        return "*" * len(plaintext)
    return "*" * (len(plaintext) - visible_suffix) + plaintext[-visible_suffix:]
