from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth_router, eval_router, packs_router
from app.config import settings
from app.core.embeddings import get_embedding_model
from app.core.pack_store import MultiPackStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("geo_policy.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Booting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    embedding_model = get_embedding_model()
    app.state.pack_store = MultiPackStore(embedding_model, settings.PACKS_DIR)
    app.state.pack_executor = ThreadPoolExecutor(
        max_workers=settings.PACK_EXECUTOR_MAX_WORKERS, thread_name_prefix="geo-policy"
    )
    app.state.default_threshold = settings.DEFAULT_DISTANCE_THRESHOLD
    logger.info("Loaded packs: %s", [p["pack_id"] for p in app.state.pack_store.list_packs()])
    yield
    app.state.pack_executor.shutdown(wait=True)
    logger.info("Geo-Compliance Policy Engine shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Independent, pre-built, per-country/regime policy packs, evaluated concurrently with short-circuit blocking.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(packs_router)
app.include_router(eval_router)


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}
