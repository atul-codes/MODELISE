"""
Client wrapper around PolicyEnforcementService's gRPC API. grpcio's
Python API is synchronous, so calls go through asyncio's default executor
to avoid blocking the event loop - same reasoning as every other blocking
call in this system (see guardrail_layer2's embeddings.py for the fuller
explanation).
"""

from __future__ import annotations

import asyncio
import logging

import grpc

from src.core.config import settings
from src.integrations.pel import pel_pb2, pel_pb2_grpc

logger = logging.getLogger("modelise.pel_client")


class PELUnavailableError(RuntimeError):
    pass


_ACTION_NAMES = {0: "ALLOW", 1: "REDACT", 2: "BLOCK"}


def _inspect_text_sync(text: str) -> dict:
    with grpc.insecure_channel(settings.PEL_GRPC_ADDRESS) as channel:
        stub = pel_pb2_grpc.PolicyEnforcementStub(channel)
        request = pel_pb2.TextRequest(request_id="", text=text)
        response = stub.InspectText(request, timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS)
        return {"action": _ACTION_NAMES.get(response.action, "BLOCK"), "risk_score": response.risk_score}


def _inspect_image_sync(image_bytes: bytes, mime_type: str) -> dict:
    with grpc.insecure_channel(settings.PEL_GRPC_ADDRESS) as channel:
        stub = pel_pb2_grpc.PolicyEnforcementStub(channel)
        request = pel_pb2.ImageRequest(request_id="", image_data=image_bytes, mime_type=mime_type)
        response = stub.InspectImage(request, timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS)
        return {"action": _ACTION_NAMES.get(response.action, "BLOCK"), "risk_score": response.risk_score}


async def inspect_text(text: str) -> dict:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _inspect_text_sync, text)
    except grpc.RpcError as exc:
        logger.warning("PolicyEnforcementService InspectText call failed: %s", exc)
        raise PELUnavailableError(str(exc)) from exc


async def inspect_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, _inspect_image_sync, image_bytes, mime_type)
    except grpc.RpcError as exc:
        logger.warning("PolicyEnforcementService InspectImage call failed: %s", exc)
        raise PELUnavailableError(str(exc)) from exc
