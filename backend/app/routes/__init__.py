"""
API routes for Agent B.
"""

from fastapi import APIRouter

from .artifact_routes import router as artifact_router
from .auth_routes import router as auth_router
from .document_routes import router as document_router
from .exec_routes import router as exec_router
from .explorer_routes import router as explorer_router
from .file_routes import router as file_router
from .knowledge_routes import router as knowledge_router
from .llm_provider_config_routes import router as llm_provider_config_router
from .llm_routes import router as llm_router
from .message_routes import router as message_router
from .persona_routes import router as persona_router
from .rag_routes import router as rag_router
from .run_routes import router as run_router
from .session_routes import router as session_router
from .tool_routes import router as tool_router
from .workspace_export_import import router as workspace_xfer_router
from .paper_routes import router as paper_router
from .workspace_routes import router as workspace_router

# Main API router
api_router = APIRouter(prefix="/api/v1")

# Register sub-routers
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(exec_router, tags=["execution"])
api_router.include_router(session_router, tags=["sessions"])
api_router.include_router(message_router, tags=["messages"])
api_router.include_router(file_router, tags=["files"])
api_router.include_router(artifact_router, tags=["artifacts"])
api_router.include_router(run_router, tags=["runs"])
api_router.include_router(explorer_router, tags=["explorer"])
api_router.include_router(llm_router, tags=["llm"])
api_router.include_router(llm_provider_config_router, tags=["llm-config"])
api_router.include_router(document_router, tags=["documents"])
api_router.include_router(tool_router, tags=["tools"])
api_router.include_router(rag_router, tags=["rag"])
api_router.include_router(knowledge_router, tags=["knowledge"])
api_router.include_router(persona_router, tags=["personas"])
api_router.include_router(paper_router, tags=["papers"])
api_router.include_router(workspace_router, tags=["workspace"])
api_router.include_router(workspace_xfer_router, tags=["workspace"])

__all__ = ["api_router"]
