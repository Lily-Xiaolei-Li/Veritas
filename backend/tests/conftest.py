import sys
from pathlib import Path

# Ensure `backend/` is on sys.path so imports like `from app...` work.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
