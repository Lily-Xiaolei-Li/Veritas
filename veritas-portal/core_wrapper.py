import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).parent.parent
LEGACY_BACKEND_DIR = BASE_DIR / "backend"
LEGACY_PYTHON = LEGACY_BACKEND_DIR / ".venv" / "Scripts" / "python.exe"

def run_legacy_core(resource: str, action: str, params: Optional[list] = None) -> Dict[str, Any]:
    cmd = [str(LEGACY_PYTHON), "-m", "cli.main", "--json", resource, action]
    if params:
        cmd.extend(params)
    
    result = subprocess.run(
        cmd,
        cwd=str(LEGACY_BACKEND_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    
    if result.returncode != 0:
        try:
            return json.loads(result.stderr)
        except:
            return {"ok": False, "error": {"message": result.stderr or result.stdout}}
            
    # Try to find the JSON line in output
    for line in result.stdout.splitlines():
        if line.strip().startswith("{"):
            return json.loads(line)

    return {"ok": False, "error": {"message": "No JSON found in output", "raw": result.stdout}}
