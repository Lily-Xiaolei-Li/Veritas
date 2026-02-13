"""
Real-time Log Streaming API (WebSocket).

Provides:
- GET /api/v1/logs/recent - Get recent log entries
- WS /api/v1/logs/stream - Real-time log streaming via WebSocket
"""

import asyncio
import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.logging_config import get_logger

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])
logger = get_logger("logs")

# Store for recent logs (ring buffer)
MAX_LOG_HISTORY = 500
log_history: Deque[Dict[str, Any]] = deque(maxlen=MAX_LOG_HISTORY)

# Connected WebSocket clients
connected_clients: Set[WebSocket] = set()


class LogEntry(BaseModel):
    """Log entry model."""
    timestamp: str
    level: str
    component: str
    message: str
    extra: Dict[str, Any] = {}


class WebSocketLogHandler(logging.Handler):
    """Custom log handler that broadcasts to WebSocket clients."""
    
    def __init__(self):
        super().__init__()
        self.setLevel(logging.DEBUG)
    
    def emit(self, record: logging.LogRecord):
        """Emit a log record to all connected clients."""
        try:
            # Build log entry
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "component": record.name,
                "message": record.getMessage(),
            }
            
            # Add extra fields if present
            if hasattr(record, "extra_fields"):
                entry["extra"] = record.extra_fields
            
            # Add to history
            log_history.append(entry)
            
            # Broadcast to connected clients (non-blocking)
            if connected_clients:
                asyncio.create_task(broadcast_log(entry))
                
        except Exception:
            # Don't let logging errors crash the app
            pass


async def broadcast_log(entry: Dict[str, Any]):
    """Broadcast a log entry to all connected WebSocket clients."""
    if not connected_clients:
        return
    
    message = json.dumps(entry)
    disconnected = set()
    
    for client in connected_clients:
        try:
            await client.send_text(message)
        except Exception:
            disconnected.add(client)
    
    # Clean up disconnected clients
    for client in disconnected:
        connected_clients.discard(client)


def setup_websocket_log_handler():
    """Install the WebSocket log handler on the root logger."""
    handler = WebSocketLogHandler()
    
    # Format similar to text formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    
    logger.info("WebSocket log streaming enabled")


@router.get("/recent")
async def get_recent_logs(
    limit: int = Query(default=100, ge=1, le=500),
    level: str = Query(default=None, description="Filter by log level (DEBUG, INFO, WARNING, ERROR)")
):
    """Get recent log entries."""
    logs = list(log_history)
    
    # Filter by level if specified
    if level:
        level_upper = level.upper()
        logs = [l for l in logs if l["level"] == level_upper]
    
    # Return most recent entries
    return {"logs": logs[-limit:], "total": len(logs)}


@router.websocket("/stream")
async def websocket_log_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    await websocket.accept()
    connected_clients.add(websocket)
    
    logger.info(f"Log stream client connected. Total clients: {len(connected_clients)}")
    
    try:
        # Send recent logs as initial batch
        initial_logs = list(log_history)[-50:]  # Last 50 entries
        for entry in initial_logs:
            await websocket.send_text(json.dumps(entry))
        
        # Keep connection alive and wait for disconnect
        while True:
            try:
                # Wait for any message (ping/pong or close)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")
                    
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"Log stream error: {e}")
    finally:
        connected_clients.discard(websocket)
        logger.info(f"Log stream client disconnected. Total clients: {len(connected_clients)}")
