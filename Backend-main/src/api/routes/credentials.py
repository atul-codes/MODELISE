from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.security import encrypt_secret, get_current_admin, mask_secret
from src.database.models import CommercialProviderCredential
from src.database.session import get_db
from src.schemas.api_schemas import CredentialCreateRequest, CredentialOut

credentials_router = APIRouter(
    prefix="/api/v1/credentials", tags=["Commercial AI Credentials"], dependencies=[Depends(get_current_admin)]
)


def _to_out(row: CommercialProviderCredential, plaintext_for_mask: str | None = None) -> CredentialOut:
    # We never store the plaintext, so the mask is computed once at
    # creation time from what was just submitted, and thereafter this
    # falls back to a fixed-width mask - we deliberately do not decrypt
    # existing keys just to redisplay them.
    masked = mask_secret(plaintext_for_mask) if plaintext_for_mask else "*" * 12
    return CredentialOut(
        id=row.id, provider=row.provider, label=row.label, masked_key=masked, enabled=row.enabled,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@credentials_router.get("", response_model=list[CredentialOut])
async def list_credentials(db: Session = Depends(get_db)) -> list[CredentialOut]:
    rows = db.query(CommercialProviderCredential).all()
    return [_to_out(r) for r in rows]


@credentials_router.post("", response_model=CredentialOut)
async def create_credential(payload: CredentialCreateRequest, db: Session = Depends(get_db)) -> CredentialOut:
    row = CommercialProviderCredential(
        provider=payload.provider, label=payload.label, encrypted_api_key=encrypt_secret(payload.api_key)
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row, plaintext_for_mask=payload.api_key)


@credentials_router.put("/{credential_id}/toggle", response_model=CredentialOut)
async def toggle_credential(credential_id: str, enabled: bool, db: Session = Depends(get_db)) -> CredentialOut:
    row = db.query(CommercialProviderCredential).filter(CommercialProviderCredential.id == credential_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such credential")
    row.enabled = enabled
    db.commit()
    db.refresh(row)
    return _to_out(row)


@credentials_router.delete("/{credential_id}")
async def delete_credential(credential_id: str, db: Session = Depends(get_db)) -> dict:
    row = db.query(CommercialProviderCredential).filter(CommercialProviderCredential.id == credential_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such credential")
    db.delete(row)
    db.commit()
    return {"status": "deleted", "credential_id": credential_id}
