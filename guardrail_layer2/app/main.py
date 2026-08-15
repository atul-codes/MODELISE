from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.admin_router import router as admin_router
from app.api.v1.auth_router import router as auth_router
from app.api.v1.dashboard_router import router as dashboard_router
from app.api.v1.guardrail_router import router as guardrail_router
from app.config import settings
from app.core.cost_guard import BudgetLedger, HighCostGate
from app.core.embeddings import get_embedding_model
from app.core.vector_store import PolicyVectorStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("modelise.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Owns the lifecycle of every shared, stateful resource the service
    needs: the embedding model, the FAISS policy store, the budget ledger,
    the rate gate, a pooled httpx client for Ollama, and the thread pool
    that keeps Gate 2's embedding/search work off the event loop. All of it
    lives on `app.state` rather than as module-level globals, which keeps
    resource lifetime tied to the app instance and makes the service
    straightforward to test in isolation."""
    logger.info("Booting %s v%s (%s)", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)

    embedding_model = get_embedding_model()
    app.state.vector_store = PolicyVectorStore(embedding_model, settings.VECTOR_INDEX_DIR)
    app.state.budget_ledger = BudgetLedger(settings.LEDGER_FILE)
    app.state.rate_gate = HighCostGate()
    app.state.faiss_threshold = settings.FAISS_DISTANCE_THRESHOLD
    app.state.ollama_client = httpx.AsyncClient(timeout=settings.OLLAMA_REQUEST_TIMEOUT_SECONDS)
    app.state.chunk_executor = ThreadPoolExecutor(
        max_workers=settings.VECTOR_EXECUTOR_MAX_WORKERS,
        thread_name_prefix="modelise-vector",
    )

    logger.info(
        "Policy index ready: %s | Ollama: %s (eval=%s, gen=%s) | threshold=%.3f",
        app.state.vector_store.stats(),
        settings.OLLAMA_BASE_URL,
        settings.OLLAMA_EVAL_MODEL,
        settings.OLLAMA_GEN_MODEL,
        app.state.faiss_threshold,
    )

    yield

    await app.state.ollama_client.aclose()
    app.state.chunk_executor.shutdown(wait=True)
    logger.info("Layer 2 shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "MODELISE Layer 2 - Custom Organizational Policy Enforcement, Semantic "
        "Token-Burn Exploit Defense, and Local LLM Orchestration Engine. Sits "
        "behind Layer 1 and in front of a locally-hosted generation model."
    ),
    lifespan=lifespan,
)

# Bearer-token auth (not cookies) doesn't need CORS credentials mode, so
# allow_credentials stays False - that also lets allow_origins safely stay
# a wildcard for local development. Tighten both before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(guardrail_router)
app.include_router(dashboard_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "error", "detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "detail": "Internal server error"},
    )


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}
