import httpx
from typing import Dict, Any, Optional, List
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1/sh"

class HollowsBridge:
    def __init__(self, timeout: float = 60.0):
        self.timeout = timeout

    def check_health(self) -> Dict[str, Any]:
        try:
            with httpx.Client(timeout=5.0) as client:
                r = client.get(f"{BASE_URL}/health")
                return {"ok": r.status_code == 200, "data": r.json() if r.status_code == 200 else r.text}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def cast_vf(self, document_id: str, mode: str = "full") -> Dict[str, Any]:
        """Veritafactum: Citation Verification"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(f"{BASE_URL}/veritafactum/check", json={
                    "document_id": document_id,
                    "mode": mode
                })
                r.raise_for_status()
                return {"ok": True, "data": r.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def cast_ci(self, sentence: str, context: str = "", top_k: int = 5) -> Dict[str, Any]:
        """Citalio: Citation Recommendation"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(f"{BASE_URL}/citalio/recommend", json={
                    "sentence": sentence,
                    "context": context,
                    "top_k": top_k
                })
                r.raise_for_status()
                return {"ok": True, "data": r.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def cast_pm(self, paper_ids: List[str], depth: int = 2, max_papers: int = 50) -> Dict[str, Any]:
        """Proliferomaxima: Network Expansion"""
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(f"{BASE_URL}/proliferomaxima/expand", json={
                    "paper_ids": paper_ids,
                    "depth": depth,
                    "max_papers": max_papers
                })
                r.raise_for_status()
                return {"ok": True, "data": r.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def cast_ep(self, target: str, out_dir: str = "./grimoire") -> Dict[str, Any]:
        """Ex-portario: PDF Retrieval"""
        try:
            # Note: This might be a long running download
            with httpx.Client(timeout=300.0) as client:
                r = client.post(f"{BASE_URL}/exportario/retrieve", json={
                    "target": target,
                    "out_dir": out_dir
                })
                r.raise_for_status()
                return {"ok": True, "data": r.json()}
        except Exception as e:
            return {"ok": False, "error": str(e)}
