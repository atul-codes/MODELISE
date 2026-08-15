from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.security import encrypt_secret, get_current_admin
from src.database.models import CustomModelEndpoint
from src.database.session import get_db
from src.schemas.api_schemas import CustomModelCreateRequest, CustomModelOut

custom_models_router = APIRouter(
    prefix="/api/v1/custom-models", tags=["Custom Model Endpoints"], dependencies=[Depends(get_current_admin)]
)

_ALLOWED_SCHEMES = {"http", "https"}


def _validate_base_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES or not parsed.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="base_url must be a valid http:// or https:// URL",
        )


def _to_out(row: CustomModelEndpoint) -> CustomModelOut:
    return CustomModelOut(
        id=row.id,
        name=row.name,
        base_url=row.base_url,
        request_style=row.request_style,
        auth_header_name=row.auth_header_name,
        has_auth=bool(row.encrypted_auth_value),
        enabled=row.enabled,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@custom_models_router.get("", response_model=list[CustomModelOut])
async def list_custom_models(db: Session = Depends(get_db)) -> list[CustomModelOut]:
    rows = db.query(CustomModelEndpoint).all()
    return [_to_out(r) for r in rows]


@custom_models_router.post("", response_model=CustomModelOut)
async def register_custom_model(payload: CustomModelCreateRequest, db: Session = Depends(get_db)) -> CustomModelOut:
    """
    Registering an endpoint here is deliberately admin-only: this is where
    'connect your self-hosted model via a local endpoint' becomes real, and
    since these are typically localhost / private-network addresses by
    design (that's the whole point - it's YOUR model), we don't block
    private IP ranges the way a public-facing URL-fetch feature normally
    would. What we do enforce: only an authenticated admin can register
    one, only http(s) schemes are accepted, and any auth header value is
    encrypted at rest immediately.
    """
    _validate_base_url(payload.base_url)

    encrypted_auth = encrypt_secret(payload.auth_header_value) if payload.auth_header_value else None

    row = CustomModelEndpoint(
        name=payload.name,
        base_url=payload.base_url,
        request_style=payload.request_style,
        auth_header_name=payload.auth_header_name,
        encrypted_auth_value=encrypted_auth,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@custom_models_router.put("/{endpoint_id}/toggle", response_model=CustomModelOut)
async def toggle_custom_model(endpoint_id: str, enabled: bool, db: Session = Depends(get_db)) -> CustomModelOut:
    row = db.query(CustomModelEndpoint).filter(CustomModelEndpoint.id == endpoint_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such custom model endpoint")
    row.enabled = enabled
    db.commit()
    db.refresh(row)
    return _to_out(row)


@custom_models_router.delete("/{endpoint_id}")
async def delete_custom_model(endpoint_id: str, db: Session = Depends(get_db)) -> dict:
    row = db.query(CustomModelEndpoint).filter(CustomModelEndpoint.id == endpoint_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such custom model endpoint")
    db.delete(row)
    db.commit()
    return {"status": "deleted", "endpoint_id": endpoint_id}
