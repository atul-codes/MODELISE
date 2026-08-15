from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Must happen before any `app.*` module is imported, since app.core.embeddings
# does `from sentence_transformers import SentenceTransformer` at import time.
sys.path.insert(0, str(Path(__file__).parent))
import _fake_sentence_transformers  # noqa: E402

sys.modules["sentence_transformers"] = _fake_sentence_transformers

import os  # noqa: E402

# app/config.py builds one frozen `settings` singleton the first time it is
# imported, and the rest of the app does `from app.config import settings`
# rather than re-resolving settings per call - correct for a real running
# process, but it means env vars have to be in place BEFORE the first
# `app.*` import happens, once, for the whole test session (not per-test).
_scratch = Path(tempfile.mkdtemp(prefix="modelise_test_"))
(_scratch / "vector_indices").mkdir()
(_scratch / "data").mkdir()

os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-admin-password"
os.environ["DEFAULT_USER_BUDGET_USD"] = "5.0"
os.environ["VECTOR_INDEX_DIR"] = str(_scratch / "vector_indices")
os.environ["LEDGER_FILE"] = str(_scratch / "data" / "ledger.json")

import httpx  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.config import get_settings  # noqa: E402

settings = get_settings()


@pytest_asyncio.fixture()
async def client():
    """A real httpx.AsyncClient talking to the real FastAPI app in-process
    (ASGITransport), with the real lifespan startup/shutdown triggered -
    this exercises the exact app.state wiring main.py uses in production,
    just without a live Ollama behind it. The FAISS index on disk persists
    across tests within the session, matching how the real service behaves
    across restarts."""
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest_asyncio.fixture()
async def admin_token(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
