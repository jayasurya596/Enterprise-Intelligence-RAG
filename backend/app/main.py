import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import engine, get_db, init_db
from app.routes_auth import router as auth_router
from app.routes_chat import router as chat_router
from app.routes_documents import router as documents_router
from app.vector_index import get_vector_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    startup()
    yield


app = FastAPI(title="Enterprise Intelligence RAG API", version="0.1.0", description="Authenticated, citation-grounded document intelligence MVP", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"])
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)


@app.middleware("http")
async def request_observability(request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started = perf_counter()
    response = await call_next(request)
    elapsed_ms = round((perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logging.getLogger("request").info("request_id=%s method=%s path=%s status=%s duration_ms=%s", request_id, request.method, request.url.path, response.status_code, elapsed_ms)
    return response


def startup() -> None:
    if settings.app_env.casefold() == "production" and (settings.app_secret_key == "development-only-change-me-before-sharing" or len(settings.app_secret_key) < 32):
        raise RuntimeError("Production requires a unique APP_SECRET_KEY of at least 32 characters.")
    if settings.app_env.casefold() == "production":
        raise RuntimeError("Production startup is blocked: this build has no real email/phone OTP or verified identity provider. See docs/FREE-TIER-PLAN.md.")
    # Production deployments apply Alembic migrations as a one-off rollout step.
    # Keep create_all limited to local development and test startup.
    if settings.app_env.casefold() != "production":
        init_db()
    settings.upload_dir.resolve().mkdir(parents=True, exist_ok=True)


@app.get("/health/live", tags=["health"])
def live():
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        get_vector_index().health()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="A required dependency is not ready.") from exc
    return {"status": "ready", "database": "ok", "vector_store": "ok"}


@app.get("/", include_in_schema=False)
def root():
    return {"name": "Enterprise Intelligence RAG", "docs": "/docs", "health": "/health/live"}

