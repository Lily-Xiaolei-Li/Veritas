import logging
import sys
from pathlib import Path

# Add parent to path for absolute imports when running standalone
sys.path.insert(0, str(Path(__file__).parent))

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
