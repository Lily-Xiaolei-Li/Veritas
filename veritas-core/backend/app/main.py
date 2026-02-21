"""
Veritas Core - Main Entry Point

FastAPI application for Veritas Core with plugin system.
"""

import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .plugins import PluginManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 全局插件管理器
plugin_manager = PluginManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - startup and shutdown events."""
    # Startup
    logger.info("Starting Veritas Core...")
    loaded = plugin_manager.load_all(app)
    logger.info(f"Veritas Core started. {loaded} plugin(s) loaded.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Veritas Core...")


app = FastAPI(
    title="Veritas Core",
    description="Veritas Core API - Plugin-based Research Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "service": "veritas-core"
    }


@app.get("/api/v1/plugins")
async def list_plugins() -> List[dict]:
    """
    列出所有已发现的插件
    
    Returns:
        List of plugin manifests with load status
    """
    plugins = plugin_manager.discover()
    
    # 添加加载状态
    for plugin in plugins:
        plugin_name = plugin.get("name")
        if plugin_name:
            plugin["loaded"] = plugin_manager.is_loaded(plugin_name)
    
    return plugins
