from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_STATE_FILE = Path(__file__).resolve().parents[1] / ".agentb_cli_state.json"
API_BASE_URL = os.getenv("AGENTB_API_URL", "http://localhost:8000/api/v1")
API_TIMEOUT = 10.0

# Set to True to use Backend API (shared with GUI)
# Set to False to use local JSON file (CLI-only mode)
USE_API_MODE = os.getenv("AGENTB_USE_API", "true").lower() == "true"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def state_file() -> Path:
    override = os.getenv("AGENTB_STATE_FILE")
    if override:
        return Path(override)
    return DEFAULT_STATE_FILE


def _default_state() -> dict[str, Any]:
    return {
        "sessions": [],
        "current_session_id": None,
        "idempotency": {},
        "contexts": {"global": None, "sessions": {}, "runs": {}},
        "sources": [],
        "personas": [],
        "artifacts": [],
        "runs": [],
        "messages": [],
    }


def ensure_state_keys(state: dict[str, Any]) -> dict[str, Any]:
    defaults = _default_state()
    for key, val in defaults.items():
        if key not in state:
            state[key] = val
    return state


# =============================================================================
# API Client Functions
# =============================================================================

def _api_available() -> bool:
    """Check if Backend API is available."""
    if not USE_API_MODE:
        return False
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{API_BASE_URL.replace('/api/v1', '')}/health")
            return response.status_code == 200
    except Exception:
        return False


def _fetch_from_api(endpoint: str) -> Optional[list]:
    """Fetch data from Backend API."""
    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.get(f"{API_BASE_URL}/{endpoint}")
            if response.status_code == 200:
                data = response.json()
                # Handle different response formats
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    # Try common keys
                    for key in [endpoint, "items", "data", "results"]:
                        if key in data and isinstance(data[key], list):
                            return data[key]
                    return [data] if data else []
            return None
    except Exception:
        return None


def _post_to_api(endpoint: str, data: dict) -> Optional[dict]:
    """Post data to Backend API."""
    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.post(f"{API_BASE_URL}/{endpoint}", json=data)
            if response.status_code in (200, 201):
                return response.json()
            return None
    except Exception:
        return None


def _put_to_api(endpoint: str, data: dict) -> Optional[dict]:
    """Put data to Backend API."""
    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.put(f"{API_BASE_URL}/{endpoint}", json=data)
            if response.status_code == 200:
                return response.json()
            return None
    except Exception:
        return None


def _delete_from_api(endpoint: str) -> bool:
    """Delete from Backend API."""
    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.delete(f"{API_BASE_URL}/{endpoint}")
            return response.status_code in (200, 204)
    except Exception:
        return False


# =============================================================================
# State Management (Hybrid: API + Local Fallback)
# =============================================================================

def load_state() -> dict[str, Any]:
    """
    Load state from Backend API if available, otherwise from local file.
    This enables GUI and CLI to share the same data.
    """
    if USE_API_MODE and _api_available():
        state = _default_state()
        
        # Fetch from API endpoints
        sessions = _fetch_from_api("sessions")
        if sessions is not None:
            state["sessions"] = sessions
        
        personas = _fetch_from_api("personas")
        if personas is not None:
            state["personas"] = personas
        
        # Note: artifacts, runs, messages are session-scoped
        # They'll be fetched when needed by handlers
        
        # Also load local state for CLI-specific data (idempotency, current_session_id)
        local_state = _load_local_state()
        state["current_session_id"] = local_state.get("current_session_id")
        state["idempotency"] = local_state.get("idempotency", {})
        state["contexts"] = local_state.get("contexts", {"global": None, "sessions": {}, "runs": {}})
        
        return ensure_state_keys(state)
    else:
        return _load_local_state()


def _load_local_state() -> dict[str, Any]:
    """Load state from local JSON file."""
    path = state_file()
    if not path.exists():
        return _default_state()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return _default_state()
        return ensure_state_keys(raw)
    except Exception:
        return _default_state()


def save_state(state: dict[str, Any]) -> None:
    """
    Save state to Backend API if available, and always to local file.
    """
    # Always save CLI-specific data locally
    _save_local_state(state)
    
    # API sync happens through specific operations (create, update, delete)
    # Not through bulk state save, to avoid conflicts


def _save_local_state(state: dict[str, Any]) -> None:
    """Save state to local JSON file."""
    path = state_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ensure_state_keys(state), ensure_ascii=False, indent=2), encoding="utf-8")


# =============================================================================
# API-Aware CRUD Operations (for handlers to use)
# =============================================================================

def create_session_api(name: str, session_id: str) -> Optional[dict]:
    """Create session via API."""
    if USE_API_MODE and _api_available():
        result = _post_to_api("sessions", {"name": name, "id": session_id})
        if result:
            return result.get("session") or result
    return None


def get_sessions_api() -> Optional[list]:
    """Get all sessions via API."""
    if USE_API_MODE and _api_available():
        return _fetch_from_api("sessions")
    return None


def create_persona_api(name: str, system_prompt: str, persona_id: str) -> Optional[dict]:
    """Create persona via API."""
    if USE_API_MODE and _api_available():
        result = _post_to_api("personas", {
            "name": name,
            "system_prompt": system_prompt,
            "id": persona_id
        })
        if result:
            return result.get("persona") or result
    return None


def get_personas_api() -> Optional[list]:
    """Get all personas via API."""
    if USE_API_MODE and _api_available():
        return _fetch_from_api("personas")
    return None


def update_session_persona_api(session_id: str, persona_id: str) -> bool:
    """Update session's active persona via API."""
    if USE_API_MODE and _api_available():
        result = _put_to_api(f"sessions/{session_id}", {"active_persona_id": persona_id})
        return result is not None
    return False


def get_session_artifacts_api(session_id: str) -> Optional[list]:
    """Get artifacts for a session via API."""
    if USE_API_MODE and _api_available():
        return _fetch_from_api(f"sessions/{session_id}/artifacts")
    return None


def create_artifact_api(session_id: str, run_id: str, name: str, content: str, artifact_type: str = "markdown") -> Optional[dict]:
    """Create artifact via API."""
    if USE_API_MODE and _api_available():
        result = _post_to_api("artifacts", {
            "session_id": session_id,
            "run_id": run_id,
            "name": name,
            "content": content,
            "type": artifact_type
        })
        if result:
            return result.get("artifact") or result
    return None
