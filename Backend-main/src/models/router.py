"""
Feature 1: custom self-hosted model routing.

Distinct from `models/registry.py`'s upload-a-file-and-sandbox-run path -
this is "the user already has a model running somewhere reachable (Ollama,
vLLM, a plain Flask server, whatever) and just wants MODELISE to call it",
via a CustomModelEndpoint row registered through the GUI.

Two request styles are supported because most self-hosted servers speak
one of these two shapes:
- "openai_chat": POST {"messages": [...]}, read .choices[0].message.content
  (this is what Ollama, vLLM, LM Studio, text-generation-webui all speak)
- "raw_text": POST {"prompt": "..."}, treat the whole response body as text
"""

from __future__ import annotations

import logging

import httpx
from fastapi import HTTPException, status

from src.core.config import settings
from src.core.security import decrypt_secret
from src.database.models import CustomModelEndpoint

logger = logging.getLogger("modelise.custom_model_router")


async def call_custom_model(endpoint: CustomModelEndpoint, prompt: str, max_output_tokens: int = 512) -> str:
    headers = {}
    if endpoint.auth_header_name and endpoint.encrypted_auth_value:
        headers[endpoint.auth_header_name] = decrypt_secret(endpoint.encrypted_auth_value)

    try:
        async with httpx.AsyncClient(timeout=settings.DOWNSTREAM_TIMEOUT_SECONDS) as client:
            if endpoint.request_style == "raw_text":
                response = await client.post(
                    endpoint.base_url, json={"prompt": prompt, "max_tokens": max_output_tokens}, headers=headers
                )
                response.raise_for_status()
                return response.text

            # default: openai_chat
            response = await client.post(
                endpoint.base_url,
                json={
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_output_tokens,
                    "stream": False,
                },
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except httpx.HTTPError as exc:
        logger.warning("Custom model endpoint '%s' call failed: %s", endpoint.name, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Custom model '{endpoint.name}' call failed: {exc}"
        ) from exc
    except (KeyError, IndexError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Custom model '{endpoint.name}' returned an unexpected response shape",
        ) from exc
