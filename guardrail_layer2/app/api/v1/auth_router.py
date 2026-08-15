from fastapi import APIRouter, HTTPException, status

from app.core.security import create_access_token, get_admin, verify_password
from app.models.auth_schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse, summary="Admin login - returns a bearer JWT")
async def login(payload: LoginRequest) -> TokenResponse:
    admin = get_admin(payload.username)
    if admin is None or not verify_password(payload.password, admin["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token, expires_in = create_access_token(subject=payload.username, role="admin")
    return TokenResponse(access_token=token, expires_in=expires_in, role="admin")
