import os
import sys
from contextlib import asynccontextmanager

# Força UTF-8 no stdout/stderr — necessário no Windows para evitar erros charmap
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.routers import upload, jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    os.makedirs(settings.storage_upload_dir, exist_ok=True)
    os.makedirs(settings.storage_output_dir, exist_ok=True)
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
    return app


app = create_app()
