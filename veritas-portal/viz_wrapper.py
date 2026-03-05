import httpx
import subprocess
from typing import Dict, Any, Optional
from rich.console import Console

console = Console()

VIZ_URL = "http://localhost:1880"

def get_viz_health() -> Dict[str, Any]:
    try:
        with httpx.Client(timeout=1.0) as client:
            response = client.get(f"{VIZ_URL}/health")
            if response.status_code == 200:
                return {"ok": True, "data": response.json()}
            return {"ok": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_docker_status() -> Dict[str, Any]:
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=gp-viz", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            check=True
        )
        status = result.stdout.strip()
        if status:
            return {"ok": True, "status": status}
        return {"ok": False, "error": "Container not found or stopped"}
    except Exception as e:
        return {"ok": False, "error": "Docker not running or not installed"}
