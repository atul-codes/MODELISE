"""
Feature 2: commercial AI provider proxy. One function per provider, all
returning the same (text, prompt_tokens, completion_tokens) shape so the
chat route doesn't need to know which provider it's talking to.

API keys never touch this module in plaintext from storage - callers
decrypt a CommercialProviderCredential row via core/security.py and pass
the plaintext key in, used once for the outbound request, then discarded
(nothing here logs or persists it).
"""

from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException, status

from src.core.config import settings

logger = logging.getLogger("modelise.llm_service")


async def call_openai(api_key: str, prompt: str, model: str = "gpt-4o-mini", max_tokens: int = 512) -> tuple[str, int, int]:
    try:
        async with httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.OPENAI_API_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens},
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return text, int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"OpenAI call failed: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"OpenAI call failed: {exc}") from exc


async def call_anthropic(api_key: str, prompt: str, model: str = "claude-sonnet-4-6", max_tokens: int = 512) -> tuple[str, int, int]:
    try:
        async with httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.ANTHROPIC_API_BASE}/messages",
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            data = response.json()
            text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
            usage = data.get("usage", {})
            return text, int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Anthropic call failed: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Anthropic call failed: {exc}") from exc


async def call_gemini(api_key: str, prompt: str, model: str = "gemini-2.0-flash", max_tokens: int = 512) -> tuple[
    str, int, int]:
    # Strip any leading "models/" prefix so the URL is never duplicated
    clean_model = model.replace("models/", "").strip()

    try:
        async with httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.GEMINI_API_BASE}/models/{clean_model}:generateContent",
                params={"key": api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": max_tokens},
                },
            )
            response.raise_for_status()
            data = response.json()

            # Safe candidate parsing
            candidates = data.get("candidates", [])
            if not candidates or "content" not in candidates[0]:
                raise KeyError("No candidate content returned by Gemini API")

            parts = candidates[0]["content"].get("parts", [])
            text = parts[0].get("text", "") if parts else ""

            usage = data.get("usageMetadata", {})
            return text, int(usage.get("promptTokenCount", 0)), int(usage.get("candidatesTokenCount", 0))

    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail=f"Gemini call failed: {exc.response.text}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Gemini call failed: {exc}") from exc
    except (KeyError, IndexError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gemini returned an unexpected response shape or blocked the prompt: {exc}"
        ) from exc

PROVIDER_DISPATCH = {
    "openai": call_openai,
    "anthropic": call_anthropic,
    "gemini": call_gemini,
}


async def call_commercial_provider(provider: str, api_key: str, prompt: str, model: str | None = None, max_tokens: int = 512) -> tuple[str, int, int]:
    fn = PROVIDER_DISPATCH.get(provider)
    if fn is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown commercial provider '{provider}'")
    kwargs = {"max_tokens": max_tokens}
    if model:
        kwargs["model"] = model
    return await fn(api_key, prompt, **kwargs)
