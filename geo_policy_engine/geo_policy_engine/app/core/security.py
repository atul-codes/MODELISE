# from __future__ import annotations
#
# from datetime import datetime, timedelta, timezone
# from typing import Any
#
# import jwt
# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from passlib.context import CryptContext
#
# from ..config import settings
#
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# # oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)
# # Change OAuth2PasswordBearer to APIKeyHeader
# from fastapi.security import APIKeyHeader
#
# # This will just display a simple text box asking for the token string
# oauth2_scheme = APIKeyHeader(name="Authorization", auto_error=True)
#
# _ADMIN_DIRECTORY: dict[str, dict[str, str]] = {
#     settings.ADMIN_USERNAME: {
#         "username": settings.ADMIN_USERNAME,
#         "password_hash": pwd_context.hash(settings.ADMIN_PASSWORD),
#     }
# }
#
#
# def get_admin(username: str) -> dict[str, str] | None:
#     print(f"--- DEBUG AUTH ---")
#     print(f"Looking for username: {username}")
#     print(f"Stored admin username in memory: {settings.ADMIN_USERNAME}")
#     print(f"Is target username in directory? {username in _ADMIN_DIRECTORY}")
#     print(f"------------------")
#     return _ADMIN_DIRECTORY.get(username)
#
#
# def verify_password(plain: str, hashed: str) -> bool:
#     print(f"--- DEBUG AUTH ---")
#     print(f"Looking for pswd: {plain}")
#     print(f"Stored admin pswd in memory: {settings.ADMIN_PASSWORD}")
#     print(f"Is target pswd in directory? {plain in _ADMIN_DIRECTORY}")
#     print(f"------------------")
#     return pwd_context.verify(plain, hashed)
#
#
# def create_access_token(subject: str, role: str) -> tuple[str, int]:
#     expire_minutes = settings.JWT_EXPIRE_MINUTES
#     expire_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
#     payload: dict[str, Any] = {"sub": subject, "role": role, "exp": expire_at, "iat": datetime.now(timezone.utc)}
#     token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
#     return token, expire_minutes * 60
#
#
# async def get_current_admin(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
#     try:
#         payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
#     except jwt.ExpiredSignatureError as exc:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired") from exc
#     except jwt.InvalidTokenError as exc:
#         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc
#     if payload.get("role") != "admin":
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
#     return payload


from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
# Cleaned up imports at the top
from fastapi.security import APIKeyHeader
from passlib.context import CryptContext

from ..config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# This will display a simple text box in Swagger asking for your token string
oauth2_scheme = APIKeyHeader(name="Authorization", auto_error=True)

_ADMIN_DIRECTORY: dict[str, dict[str, str]] = {
    settings.ADMIN_USERNAME: {
        "username": settings.ADMIN_USERNAME,
        "password_hash": pwd_context.hash(settings.ADMIN_PASSWORD),
    }
}


def get_admin(username: str) -> dict[str, str] | None:
    print(f"--- DEBUG AUTH ---")
    print(f"Looking for username: {username}")
    print(f"Stored admin username in memory: {settings.ADMIN_USERNAME}")
    print(f"Is target username in directory? {username in _ADMIN_DIRECTORY}")
    print(f"------------------")
    return _ADMIN_DIRECTORY.get(username)


def verify_password(plain: str, hashed: str) -> bool:
    print(f"--- DEBUG AUTH ---")
    print(f"Looking for pswd: {plain}")
    print(f"Stored admin pswd in memory: {settings.ADMIN_PASSWORD}")
    print(f"------------------")
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: str) -> tuple[str, int]:
    expire_minutes = settings.JWT_EXPIRE_MINUTES
    expire_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "role": role, "exp": expire_at, "iat": datetime.now(timezone.utc)}
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, expire_minutes * 60


async def get_current_admin(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    # If the token contains the "Bearer " prefix from Swagger, strip it out before decoding
    if token.startswith("Bearer "):
        token = token.split(" ")[1]

    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token") from exc
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return payload