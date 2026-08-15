from fastapi import APIRouter, HTTPException, status

from src.core.security import create_access_token, get_admin, verify_password
from src.schemas.api_schemas import LoginRequest, TokenResponse

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@auth_router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    admin = get_admin(payload.username)
    if admin is None or not verify_password(payload.password, admin["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    token, expires_in = create_access_token(subject=payload.username, role="admin")
    return TokenResponse(access_token=token, expires_in=expires_in)
