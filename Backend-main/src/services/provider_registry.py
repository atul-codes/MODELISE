"""
The plug-and-play registry: read/write InspectionProvider rows, and
resolve which providers are active for a given pipeline name. This is the
one piece of code every "attach anything anywhere" feature routes through
- input_guard.py, policy_engine.py, and the chat routes all call
`get_providers_for_pipeline` rather than hardcoding which backends they
consult.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.database.models import InspectionProvider

DEFAULT_PROVIDER_SEEDS = [
    {
        "name": "Layer 1 - Heuristic Prompt Screen",
        "description": "Fast pattern-based prompt-injection / jailbreak screen. Always runs first, in-process, no network hop.",
        "kind": "layer1_heuristic",
        "stage": "layer1",
        "config": {},
        "attached_pipelines": ["custom_model_default", "commercial_ai_default"],
        "priority": 10,
    },
    {
        "name": "Layer 1 - Image/NSFW Check (PEL)",
        "description": "Routes any image attached to the request through PolicyEnforcementService's InspectImage RPC.",
        "kind": "layer1_image_nsfw_grpc",
        "stage": "layer1",
        "config": {},
        "attached_pipelines": ["custom_model_default", "commercial_ai_default"],
        "priority": 20,
    },
    {
        "name": "Layer 2 - guardrail_layer2 (FAISS)",
        "description": "Custom organizational policy RAG - the default Layer 2 provider.",
        "kind": "layer2_faiss_rest",
        "stage": "layer2",
        "config": {},
        "attached_pipelines": ["custom_model_default", "commercial_ai_default"],
        "priority": 30,
    },
    {
        "name": "Layer 2 - PolicyEnforcementService (gRPC classifier)",
        "description": "Alternate Layer 2 provider: local Keras text classifier over gRPC. Disabled by default - enable to run it alongside or instead of the FAISS engine.",
        "kind": "layer2_grpc_classifier",
        "stage": "layer2",
        "config": {},
        "attached_pipelines": [],
        "enabled": False,
        "priority": 40,
    },
]


def seed_default_providers(db: Session) -> None:
    """Idempotent: only inserts providers whose `kind` isn't already present,
    so re-running this on every startup never duplicates rows or clobbers
    an admin's toggle/attachment changes."""
    existing_kinds = {row.kind for row in db.query(InspectionProvider).all()}
    for seed in DEFAULT_PROVIDER_SEEDS:
        if seed["kind"] in existing_kinds:
            continue
        db.add(
            InspectionProvider(
                id=str(uuid.uuid4()),
                name=seed["name"],
                description=seed["description"],
                kind=seed["kind"],
                stage=seed["stage"],
                config_json=json.dumps(seed["config"]),
                attached_pipelines_json=json.dumps(seed["attached_pipelines"]),
                enabled=seed.get("enabled", True),
                priority=seed["priority"],
            )
        )
    db.commit()


def provider_to_dict(row: InspectionProvider) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description,
        "kind": row.kind,
        "stage": row.stage,
        "config": json.loads(row.config_json or "{}"),
        "attached_pipelines": json.loads(row.attached_pipelines_json or "[]"),
        "enabled": row.enabled,
        "priority": row.priority,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_providers(db: Session) -> list[dict]:
    rows = db.query(InspectionProvider).order_by(InspectionProvider.priority.asc()).all()
    return [provider_to_dict(r) for r in rows]


def get_providers_for_pipeline(db: Session, pipeline_name: str) -> list[InspectionProvider]:
    """Every ENABLED provider whose attached_pipelines list includes this
    pipeline name, ordered by priority (lower runs first / is listed
    first - most providers are still consulted concurrently by the callers,
    priority is mainly a display/tiebreak hint)."""
    rows = db.query(InspectionProvider).filter(InspectionProvider.enabled == True).order_by(InspectionProvider.priority.asc()).all()  # noqa: E712
    return [r for r in rows if pipeline_name in json.loads(r.attached_pipelines_json or "[]")]


def set_enabled(db: Session, provider_id: str, enabled: bool) -> InspectionProvider | None:
    row = db.query(InspectionProvider).filter(InspectionProvider.id == provider_id).first()
    if row is None:
        return None
    row.enabled = enabled
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def set_pipeline_attachments(db: Session, provider_id: str, pipelines: list[str]) -> InspectionProvider | None:
    row = db.query(InspectionProvider).filter(InspectionProvider.id == provider_id).first()
    if row is None:
        return None
    row.attached_pipelines_json = json.dumps(pipelines)
    row.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


def create_provider(db: Session, name: str, description: str, kind: str, stage: str, config: dict, attached_pipelines: list[str], priority: int = 100) -> InspectionProvider:
    row = InspectionProvider(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        kind=kind,
        stage=stage,
        config_json=json.dumps(config),
        attached_pipelines_json=json.dumps(attached_pipelines),
        enabled=True,
        priority=priority,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def delete_provider(db: Session, provider_id: str) -> bool:
    row = db.query(InspectionProvider).filter(InspectionProvider.id == provider_id).first()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True
