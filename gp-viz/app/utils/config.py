from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    qdrant_host: str
    qdrant_port: int
    xiaolei_url: str
    excel_path: str
    pdf_dir: str
    data_source_collection: str

    @property
    def qdrant_base_url(self) -> str:
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @classmethod
    def from_env(cls) -> "Settings":
        collection = os.getenv("GP_VECTR_COLLECTION") or os.getenv("GP_QDRANT_COLLECTION")
        if not collection:
            collection = "vf_profiles_slr"

        return cls(
            qdrant_host=os.getenv("QDRANT_HOST", "host.docker.internal"),
            qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
            xiaolei_url=os.getenv("XIAOLEI_API_URL", "http://localhost:8768"),
            excel_path=os.getenv(
                "GP_EXCEL_PATH",
                r"C:\Users\thene\OneDrive - The University Of Newcastle\Desktop\Newly Structured Folder\Paper 1\Data\Paper 1 SLR data and analysis (5 Jan 2026).xlsx",
            ),
            pdf_dir=os.getenv(
                "GP_PDF_DIR",
                r"C:\Users\thene\OneDrive - The University Of Newcastle\Desktop\Newly Structured Folder\Paper 1\Data\P1SLR Library",
            ),
            data_source_collection=collection,
        )