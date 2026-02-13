from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _split_csv(value: str | None) -> list[str]:
    if value is None:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    api_host: str
    api_port: int
    cors_enabled: bool
    cors_origins: list[str]
    rag_api_base_url: str
    rag_search_path: str
    clawdbot_mode: str
    clawdbot_endpoint: str
    buttons_path: Path
    request_timeout_s: float


_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is not None:
        return _SETTINGS

    api_host = os.environ.get("XIAOLEI_API_HOST", "0.0.0.0")
    api_port = int(os.environ.get("XIAOLEI_API_PORT", "8768"))

    cors_enabled = _bool(os.environ.get("XIAOLEI_CORS_ENABLED"), True)
    cors_origins_raw = os.environ.get("XIAOLEI_CORS_ORIGINS", "*")
    cors_origins = ["*"] if cors_origins_raw.strip() == "*" else _split_csv(cors_origins_raw)

    rag_api_base_url = os.environ.get("XIAOLEI_RAG_API_BASE_URL", "http://localhost:8767")
    rag_search_path = os.environ.get("XIAOLEI_RAG_SEARCH_PATH", "/search")

    clawdbot_mode = os.environ.get("XIAOLEI_CLAWDBOT_MODE", "mock")
    clawdbot_endpoint = os.environ.get("XIAOLEI_CLAWDBOT_ENDPOINT", "https://localhost:8765/execute")

    buttons_path_env = os.environ.get("XIAOLEI_BUTTONS_PATH")
    if buttons_path_env:
        buttons_path = Path(buttons_path_env)
    else:
        buttons_path = _repo_root() / "data" / "buttons.json"

    request_timeout_s = float(os.environ.get("XIAOLEI_REQUEST_TIMEOUT_S", "15"))

    _SETTINGS = Settings(
        api_host=api_host,
        api_port=api_port,
        cors_enabled=cors_enabled,
        cors_origins=cors_origins,
        rag_api_base_url=rag_api_base_url,
        rag_search_path=rag_search_path,
        clawdbot_mode=clawdbot_mode,
        clawdbot_endpoint=clawdbot_endpoint,
        buttons_path=buttons_path,
        request_timeout_s=request_timeout_s,
    )
    return _SETTINGS
