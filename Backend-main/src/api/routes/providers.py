from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.security import get_current_admin
from src.database.session import get_db
from src.schemas.api_schemas import (
    ProviderAttachmentsRequest,
    ProviderCreateRequest,
    ProviderOut,
    ProviderToggleRequest,
)
from src.services import provider_registry

providers_router = APIRouter(
    prefix="/api/v1/providers", tags=["Plug-and-Play Providers"], dependencies=[Depends(get_current_admin)]
)


@providers_router.get("", response_model=list[ProviderOut])
async def list_providers(db: Session = Depends(get_db)) -> list[ProviderOut]:
    return [ProviderOut(**p) for p in provider_registry.list_providers(db)]


@providers_router.post("", response_model=ProviderOut)
async def create_provider(payload: ProviderCreateRequest, db: Session = Depends(get_db)) -> ProviderOut:
    """Register a brand new inspection provider - this is the literal
    'add anything anywhere' mechanism: pick a kind, point it at a
    downstream service via `config`, and list which pipelines it should
    apply to. No code changes, no redeploy."""
    row = provider_registry.create_provider(
        db,
        name=payload.name,
        description=payload.description,
        kind=payload.kind,
        stage=payload.stage,
        config=payload.config,
        attached_pipelines=payload.attached_pipelines,
        priority=payload.priority,
    )
    return ProviderOut(**provider_registry.provider_to_dict(row))


@providers_router.put("/{provider_id}/toggle", response_model=ProviderOut)
async def toggle_provider(provider_id: str, payload: ProviderToggleRequest, db: Session = Depends(get_db)) -> ProviderOut:
    row = provider_registry.set_enabled(db, provider_id, payload.enabled)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such provider")
    return ProviderOut(**provider_registry.provider_to_dict(row))


@providers_router.put("/{provider_id}/attachments", response_model=ProviderOut)
async def set_attachments(provider_id: str, payload: ProviderAttachmentsRequest, db: Session = Depends(get_db)) -> ProviderOut:
    """This is 'attach country policy to Layer 1' etc in practice: pass the
    list of pipeline names this provider should now apply to."""
    row = provider_registry.set_pipeline_attachments(db, provider_id, payload.attached_pipelines)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such provider")
    return ProviderOut(**provider_registry.provider_to_dict(row))


@providers_router.delete("/{provider_id}")
async def delete_provider(provider_id: str, db: Session = Depends(get_db)) -> dict:
    deleted = provider_registry.delete_provider(db, provider_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such provider")
    return {"status": "deleted", "provider_id": provider_id}
