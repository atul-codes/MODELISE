"""
Feature 3 routes. Backend-main doesn't run FAISS itself for geo packs -
it proxies upload/list/toggle calls to the GeoPolicyEngine service (see
src/integrations/geo_policy_client.py) and, on every successful upload,
mirrors that pack as an InspectionProvider row (kind="geo_policy_pack") so
it shows up in the same plug-and-play registry as everything else and can
be attached to any pipeline - including Layer 1's, per your answer that
country policy should be attachable there too.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.core.security import get_current_admin
from src.database.models import InspectionProvider
from src.database.session import get_db
from src.integrations import geo_policy_client
from src.schemas.api_schemas import GeoPackOut, GeoToggleRequest

geo_router = APIRouter(prefix="/api/v1/geo-policies", tags=["Geo-Compliance"], dependencies=[Depends(get_current_admin)])


def _sync_provider_row(db: Session, pack: dict) -> None:
    """Idempotent: creates the provider row for a pack the first time it's
    seen, updates its enabled/name on every subsequent sync. Attaching it
    to pipelines is a separate step via /api/v1/providers/{id}/attachments
    - a freshly uploaded pack starts unattached (checked, not silently
    live) so nothing is enforced until an admin deliberately turns it on
    for a pipeline."""
    existing = (
        db.query(InspectionProvider)
        .filter(InspectionProvider.kind == "geo_policy_pack")
        .filter(InspectionProvider.config_json.like(f'%"pack_id": "{pack["pack_id"]}"%'))
        .first()
    )
    if existing:
        existing.name = f"Geo Policy - {pack['display_name']}"
        db.commit()
        return

    import uuid

    db.add(
        InspectionProvider(
            id=str(uuid.uuid4()),
            name=f"Geo Policy - {pack['display_name']}",
            description=f"Country/regime-specific policy pack ({pack.get('country_code') or 'n/a'}), served by the Geo Policy Engine.",
            kind="geo_policy_pack",
            stage="geo",
            config_json=json.dumps({"pack_id": pack["pack_id"], "base_url": None}),
            attached_pipelines_json="[]",
            enabled=True,
            priority=50,
        )
    )
    db.commit()


@geo_router.get("", response_model=list[GeoPackOut])
async def list_packs():
    try:
        packs = await geo_policy_client.list_packs()
    except geo_policy_client.GeoPolicyEngineUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return [GeoPackOut(**p) for p in packs]


@geo_router.post("/{pack_id}/upload-csv", response_model=GeoPackOut)
async def upload_csv(
    pack_id: str, display_name: str, country_code: str | None = None, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a .csv")
    content = await file.read()
    try:
        result = await geo_policy_client.upload_pack_csv(pack_id, display_name, country_code, file.filename, content)
    except geo_policy_client.GeoPolicyEngineUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    _sync_provider_row(db, result)
    return GeoPackOut(**result)


@geo_router.post("/{pack_id}/upload-pdf", response_model=GeoPackOut)
async def upload_pdf(
    pack_id: str, display_name: str, country_code: str | None = None, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File must be a .pdf")
    content = await file.read()
    try:
        result = await geo_policy_client.upload_pack_pdf(pack_id, display_name, country_code, file.filename, content)
    except geo_policy_client.GeoPolicyEngineUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    _sync_provider_row(db, result)
    return GeoPackOut(**result)


@geo_router.put("/{pack_id}/toggle", response_model=GeoPackOut)
async def toggle_pack(pack_id: str, payload: GeoToggleRequest):
    try:
        result = await geo_policy_client.toggle_pack(pack_id, payload.enabled)
    except geo_policy_client.GeoPolicyEngineUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return GeoPackOut(**result)
