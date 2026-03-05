import os
import shutil
import hashlib
import json
import yaml
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Monkey-patch onnxruntime to force DmlExecutionProvider if available
import onnxruntime as ort
original_init = ort.InferenceSession.__init__
def custom_init(self, path_or_bytes, sess_options=None, providers=None, provider_options=None, **kwargs):
    available = ort.get_available_providers()
    if 'DmlExecutionProvider' in available:
        if providers:
            if 'DmlExecutionProvider' not in providers:
                providers = ['DmlExecutionProvider'] + [p for p in providers if p != 'DmlExecutionProvider']
        else:
            providers = ['DmlExecutionProvider', 'CPUExecutionProvider']
    original_init(self, path_or_bytes, sess_options, providers, provider_options, **kwargs)
ort.InferenceSession.__init__ = custom_init

from docling.document_converter import DocumentConverter

from models import Source, Project, AuditLog, CodeAssignment, Extract, Code
from search_manager import index_source

def get_file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()

def get_string_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def check_integrity(project_dir: Path) -> list[str]:
    """Check integrity of sources and code assignments."""
    db_path = project_dir / "db" / "tt.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    
    issues = []
    
    with Session(engine) as session:
        # 1. Re-calculate hashes of canonical files and compare with DB
        sources = session.query(Source).all()
        for source in sources:
            source_id_str = f"S{source.source_id:04d}"
            canonical_dir = project_dir / "sources" / source_id_str / "canonical"
            
            md_file = canonical_dir / "source.md"
            if md_file.exists():
                with open(md_file, "r", encoding="utf-8") as f:
                    current_md_hash = get_string_hash(f.read())
                if current_md_hash != source.canonical_md_hash:
                    issues.append(f"Hash mismatch for source {source_id_str} canonical markdown.")
            else:
                issues.append(f"Missing canonical markdown for source {source_id_str}.")
                
            map_file = canonical_dir / "source.map.json"
            if map_file.exists():
                current_map_hash = get_file_hash(map_file)
                if current_map_hash != source.map_hash:
                    issues.append(f"Hash mismatch for source {source_id_str} canonical map.")
            else:
                issues.append(f"Missing canonical map for source {source_id_str}.")
                
        # 2. Check for orphaned CodeAssignments
        assignments = session.query(CodeAssignment).all()
        for assignment in assignments:
            extract = session.query(Extract).filter_by(extract_id=assignment.extract_id).first()
            if not extract:
                issues.append(f"Orphaned CodeAssignment {assignment.assignment_id}: references missing extract {assignment.extract_id}.")
                
            code = session.query(Code).filter_by(code_id=assignment.code_id).first()
            if not code:
                issues.append(f"Orphaned CodeAssignment {assignment.assignment_id}: references missing code {assignment.code_id}.")

        # 3. Check for FTS5 table
        result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='fts_content';")).fetchone()
        if not result:
            issues.append("Missing FTS5 search index table 'fts_content'. Run 'tt project reindex'.")
                
    return issues

def add_source(project_dir: Path, file_path: str):
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Source file not found: {file_path}")

    db_path = project_dir / "db" / "tt.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")

    with Session(engine) as session:
        project = session.query(Project).first()
        if not project:
            raise ValueError("No project found in database.")

        # Determine next Source ID
        source_count = session.query(Source).count()
        source_id_str = f"S{source_count + 1:04d}"

        source_dir = project_dir / "sources" / source_id_str
        original_dir = source_dir / "original"
        canonical_dir = source_dir / "canonical"
        derivatives_dir = source_dir / "derivatives"
        patches_dir = derivatives_dir / "patches"

        for d in [original_dir, canonical_dir, derivatives_dir, patches_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # Copy original
        target_original = original_dir / file_path.name
        shutil.copy2(file_path, target_original)
        orig_hash = get_file_hash(target_original)

        # Convert to Markdown (using fallback for TXT, else docling)
        if target_original.suffix.lower() == ".txt":
            try:
                with open(target_original, "r", encoding="utf-8") as f:
                    canonical_md = f.read()
            except UnicodeDecodeError:
                with open(target_original, "r", encoding="latin-1") as f:
                    canonical_md = f.read()
        else:
            converter = DocumentConverter()
            doc = converter.convert(target_original)
            canonical_md = doc.document.export_to_markdown()

        # Save canonical markdown
        md_file = canonical_dir / "source.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(canonical_md)
        md_hash = get_string_hash(canonical_md)

        # Save map
        map_data = {"anchors": []}
        if target_original.suffix.lower() == ".txt":
            for i, line in enumerate(canonical_md.split('\n')):
                map_data["anchors"].append({
                    "anchor": f"line:{i+1}",
                    "text": line.strip()
                })
        else:
            p_idx = 0
            t_idx = 0
            for item, level in doc.document.iterate_items():
                label_str = str(getattr(item, "label", "")).lower()
                text = getattr(item, "text", "")
                
                if label_str in ["title", "section_header", "heading"]:
                    if text:
                        map_data["anchors"].append({"anchor": f"h:{text}", "text": text})
                elif label_str in ["text", "paragraph", "list_item"]:
                    if text:
                        map_data["anchors"].append({"anchor": f"p:{p_idx}", "text": text})
                        p_idx += 1
                elif label_str == "table":
                    table_text = text
                    if not table_text and hasattr(item, "export_to_markdown"):
                        table_text = item.export_to_markdown()
                    map_data["anchors"].append({"anchor": f"table:{t_idx}", "text": table_text})
                    t_idx += 1

        map_file = canonical_dir / "source.map.json"
        with open(map_file, "w", encoding="utf-8") as f:
            json.dump(map_data, f, indent=2)
        map_hash = get_file_hash(map_file)

        # Create meta
        meta_data = {
            "id": source_id_str,
            "type": file_path.suffix.lstrip(".").lower(),
            "provenance": "docling_conversion",
            "tags": [],
            "attributes": {}
        }
        meta_file = canonical_dir / "source.meta.yaml"
        with open(meta_file, "w", encoding="utf-8") as f:
            yaml.dump(meta_data, f, sort_keys=False)

        # DB Record
        new_source = Source(
            project_id=project.project_id,
            source_type=meta_data["type"],
            source_uri=f"sources/{source_id_str}/original/{file_path.name}",
            original_hash=orig_hash,
            canonical_md_hash=md_hash,
            map_hash=map_hash,
            canonical_md_version_id="v1",
            conversion_provenance="docling",
            attributes=meta_data["attributes"]
        )
        session.add(new_source)

        audit_log = AuditLog(
            action="add_source",
            entity_type="Source",
            entity_id=source_id_str,
            user_id="cli_user",
            details={
                "file_path": str(file_path),
                "original_hash": orig_hash,
                "type": meta_data["type"]
            }
        )
        session.add(audit_log)

        session.commit()
        
        # Index the canonical markdown in FTS5
        index_source(project_dir, source_id_str, canonical_md)

        return source_id_str
