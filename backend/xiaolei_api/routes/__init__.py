from fastapi import APIRouter

from routes.buttons import router as buttons_router
from routes.chat import router as chat_router
from routes.health import router as health_router
from routes.rag import router as rag_router

api_router = APIRouter()

api_router.include_router(chat_router)
api_router.include_router(rag_router, prefix="/rag")
api_router.include_router(buttons_router)
api_router.include_router(health_router)
