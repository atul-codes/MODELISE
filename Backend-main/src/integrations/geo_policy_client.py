"""
Client for the GeoPolicyEngine service. Uses a cached service-account
token (logged in with GEO_POLICY_ENGINE_ADMIN_USERNAME/PASSWORD from
Backend-main's own config) for admin operations, so a human only ever has
to authenticate once, against Backend-main - not separately against every
downstream service it happens to call.
"""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from ..core.config import settings

logger = logging.getLogger("modelise.geo_policy_client")


class GeoPolicyEngineUnavailableError(RuntimeError):
    pass


_token_cache: dict = {"token": None, "expires_at": 0.0}
_token_lock = asyncio.Lock()


async def _get_service_token() -> str:
    async with _token_lock:
        if _token_cache["token"] and time.monotonic() < _token_cache["expires_at"] - 30:
            return _token_cache["token"]
        try:
            async with httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{settings.GEO_POLICY_ENGINE_BASE_URL}/api/v1/auth/login",
                    json={
                        "username": settings.GEO_POLICY_ENGINE_ADMIN_USERNAME,
                        "password": settings.GEO_POLICY_ENGINE_ADMIN_PASSWORD,
                    },
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            raise GeoPolicyEngineUnavailableError(f"Could not authenticate to Geo Policy Engine: {exc}") from exc

        _token_cache["token"] = body["access_token"]
        _token_cache["expires_at"] = time.monotonic() + body["expires_in"]
        return _token_cache["token"]


async def evaluate(prompt: str, pack_ids: list[str] | None = None, threshold: float | None = None) -> dict:
    """Unauthenticated per GeoPolicyEngine's own design (matches
    guardrail_layer2's evaluate endpoint) - no token needed here."""
    payload: dict = {"prompt": prompt}
    if pack_ids:
        payload["pack_ids"] = pack_ids
    if threshold is not None:
        payload["threshold"] = threshold
    try:
        async with httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS) as client:
            response = await client.post(f"{settings.GEO_POLICY_ENGINE_BASE_URL}/api/v1/evaluate", json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        logger.warning("Geo Policy Engine evaluate call failed: %s", exc)
        raise GeoPolicyEngineUnavailableError(str(exc)) from exc


async def list_packs() -> list[dict]:
    token = await _get_service_token()
    async with httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS) as client:
        response = await client.get(
            f"{settings.GEO_POLICY_ENGINE_BASE_URL}/api/v1/packs", headers={"Authorization": f"Bearer {token}"}
        )
        response.raise_for_status()
        return response.json()


async def upload_pack_csv(pack_id: str, display_name: str, country_code: str | None, filename: str, content: bytes) -> dict:
    token = await _get_service_token()
    params = {"display_name": display_name}
    if country_code:
        params["country_code"] = country_code
    async with httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{settings.GEO_POLICY_ENGINE_BASE_URL}/api/v1/packs/{pack_id}/upload-csv",
            params=params,
            files={"file": (filename, content, "text/csv")},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()


async def upload_pack_pdf(pack_id: str, display_name: str, country_code: str | None, filename: str, content: bytes) -> dict:
    token = await _get_service_token()
    params = {"display_name": display_name}
    if country_code:
        params["country_code"] = country_code
    async with httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{settings.GEO_POLICY_ENGINE_BASE_URL}/api/v1/packs/{pack_id}/upload-pdf",
            params=params,
            files={"file": (filename, content, "application/pdf")},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()


async def toggle_pack(pack_id: str, enabled: bool) -> dict:
    token = await _get_service_token()
    async with httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS) as client:
        response = await client.put(
            f"{settings.GEO_POLICY_ENGINE_BASE_URL}/api/v1/packs/{pack_id}/toggle",
            json={"enabled": enabled},
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.json()
