import logging
import sys
from pathlib import Path

# Ensure imports can resolve Veritas modules and local xiaolei_api modules.
repo_root = Path(__file__).resolve().parents[1]
backend_root = repo_root / "backend"
for path in (repo_root, backend_root):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from config import get_settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import api_router

settings = get_settings()

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="XiaoLei API", version="0.1.0")

if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router)
