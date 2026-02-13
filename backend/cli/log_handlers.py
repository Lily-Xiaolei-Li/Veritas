"""
CLI Log Handlers - Real-time log streaming.

Commands:
- log stream: Stream logs in real-time via WebSocket
- log recent: Get recent log entries
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime

import websockets

from .contract import CLIBusinessError, success_envelope
from .health import get_api_base


def _level_color(level: str) -> str:
    """ANSI color codes for log levels."""
    colors = {
        "DEBUG": "\033[90m",     # Gray
        "INFO": "\033[94m",      # Blue
        "WARNING": "\033[93m",   # Yellow
        "ERROR": "\033[91m",     # Red
        "CRITICAL": "\033[91;1m",# Bold red
    }
    return colors.get(level, "")


def _reset_color() -> str:
    return "\033[0m"


async def _stream_logs(base_url: str, level_filter: str | None, use_color: bool) -> None:
    """Connect to WebSocket and stream logs."""
    # Convert HTTP URL to WebSocket URL
    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
    ws_url = f"{ws_url}/api/v1/logs/stream"
    
    print(f"Connecting to {ws_url}...", file=sys.stderr)
    
    try:
        async with websockets.connect(ws_url) as ws:
            print("Connected. Streaming logs (Ctrl+C to stop)...\n", file=sys.stderr)
            
            while True:
                try:
                    message = await ws.recv()
                    data = json.loads(message)
                    
                    # Skip ping messages
                    if data.get("type") == "ping":
                        continue
                    
                    # Filter by level if specified
                    if level_filter and data.get("level") != level_filter.upper():
                        continue
                    
                    # Format and print log entry
                    timestamp = data.get("timestamp", "")
                    level = data.get("level", "INFO")
                    component = data.get("component", "")
                    message_text = data.get("message", "")
                    
                    # Parse timestamp for display
                    try:
                        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                        time_str = dt.strftime("%H:%M:%S")
                    except Exception:
                        time_str = timestamp[:19] if timestamp else ""
                    
                    # Format output
                    if use_color:
                        color = _level_color(level)
                        reset = _reset_color()
                        print(f"{time_str} {color}[{level:8}]{reset} {component}: {message_text}")
                    else:
                        print(f"{time_str} [{level:8}] {component}: {message_text}")
                    
                    sys.stdout.flush()
                    
                except websockets.ConnectionClosed:
                    print("\nConnection closed.", file=sys.stderr)
                    break
                    
    except Exception as e:
        raise CLIBusinessError(
            code="LOG_STREAM_FAILED",
            message=f"Failed to connect to log stream: {e}",
        )


def log_stream(args: argparse.Namespace) -> dict:
    """Stream logs in real-time via WebSocket."""
    base_url = get_api_base()
    level_filter = getattr(args, "level", None)
    use_color = sys.stdout.isatty() and not getattr(args, "no_color", False)
    
    try:
        asyncio.run(_stream_logs(base_url, level_filter, use_color))
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
    
    return success_envelope(result="stream_ended", data={})


def log_recent(args: argparse.Namespace) -> dict:
    """Get recent log entries."""
    import requests
    
    base_url = get_api_base()
    limit = getattr(args, "limit", 100)
    level_filter = getattr(args, "level", None)
    
    params = {"limit": limit}
    if level_filter:
        params["level"] = level_filter.upper()
    
    try:
        resp = requests.get(f"{base_url}/api/v1/logs/recent", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        # Print logs to console if not JSON mode
        if not getattr(args, "json", False):
            use_color = sys.stdout.isatty()
            for log in data.get("logs", []):
                timestamp = log.get("timestamp", "")
                level = log.get("level", "INFO")
                component = log.get("component", "")
                message = log.get("message", "")
                
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    time_str = dt.strftime("%H:%M:%S")
                except Exception:
                    time_str = timestamp[:19] if timestamp else ""
                
                if use_color:
                    color = _level_color(level)
                    reset = _reset_color()
                    print(f"{time_str} {color}[{level:8}]{reset} {component}: {message}")
                else:
                    print(f"{time_str} [{level:8}] {component}: {message}")
        
        return success_envelope(result="recent_logs", data=data)
        
    except Exception as e:
        raise CLIBusinessError(
            code="LOG_FETCH_FAILED",
            message=f"Failed to fetch logs: {e}",
        )
