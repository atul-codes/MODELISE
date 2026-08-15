import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.database.session import Base, engine, SessionLocal
from src.api.routes.model import model_router
from src.api.routes.auth import auth_router
from src.api.routes.providers import providers_router
from src.api.routes.custom_models import custom_models_router
from src.api.routes.credentials import credentials_router
from src.api.routes.geo_policy import geo_router
from src.api.routes.chat import chat_router
from src.core.config import settings
from src.services.provider_registry import seed_default_providers


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
logger = logging.getLogger("modelise.app")

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Booting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    db = SessionLocal()
    try:
        seed_default_providers(db)
    finally:
        db.close()
    logger.info(
        "Downstream services configured: guardrail_layer2=%s | PEL=%s | geo_policy_engine=%s",
        settings.GUARDRAIL_LAYER2_BASE_URL,
        settings.PEL_GRPC_ADDRESS,
        settings.GEO_POLICY_ENGINE_BASE_URL,
    )
    yield
    logger.info("MODELISE orchestrator shutdown complete")


app = FastAPI(title="MODELISE", version=settings.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(model_router)
app.include_router(auth_router)
app.include_router(providers_router)
app.include_router(custom_models_router)
app.include_router(credentials_router)
app.include_router(geo_router)
app.include_router(chat_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"status": "error", "detail": exc.errors()})


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}
