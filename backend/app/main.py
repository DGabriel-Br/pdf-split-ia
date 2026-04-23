import logging
import os
import sys
from contextlib import asynccontextmanager

# Force UTF-8 on Windows stdout/stderr to avoid charmap errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.routers import upload, jobs
from app.services.job_store import job_store

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    settings = get_settings()
    os.makedirs(settings.storage_upload_dir, exist_ok=True)
    os.makedirs(settings.storage_output_dir, exist_ok=True)

    removed = job_store.cleanup_old_files(
        settings.storage_upload_dir,
        settings.storage_output_dir,
        settings.job_ttl_seconds,
    )
    if removed:
        log.info("Limpeza inicial: %d arquivo(s) removido(s)", removed)

    yield


def create_app() -> FastAPI:
    app = FastAPI(title="PDF Split IA", version="0.1.0", lifespan=lifespan)
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(upload.router, tags=["upload"])
    app.include_router(jobs.router, tags=["jobs"])

    frontend_dist = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
    )
    if os.path.isdir(frontend_dist):
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


app = create_app()
