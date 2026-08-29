import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.exceptions import AppException
from app.routers import auth, jobs

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Best-effort: a VideoJob stuck in a non-terminal status whose RQ job
    # Redis no longer recognizes means the worker that was processing it
    # died. Runs here too (not just in worker.py) so recovery still
    # happens even if only the API process restarts. Never let this block
    # startup - Redis being briefly unavailable shouldn't take the API down.
    from app.database import SessionLocal
    from app.services.orphan_recovery import recover_orphaned_jobs

    db = SessionLocal()
    try:
        recovered = recover_orphaned_jobs(db)
        if recovered:
            logger.warning("Recovered %d orphaned job(s) on startup", recovered)
    except Exception:  # noqa: BLE001 - must never block app startup
        logger.exception("Orphaned-job recovery failed on startup (continuing anyway)")
    finally:
        db.close()

    yield


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message, "code": exc.code},
    )


# Module routers are included here (added by module agents in Phase 2)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "healthy"}
