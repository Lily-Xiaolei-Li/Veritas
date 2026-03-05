import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import Code, CodeAssignment, Extract, AuditLog

def get_db_engine(project_dir: Path):
    db_path = project_dir / "db" / "tt.sqlite"
    return create_engine(f"sqlite:///{db_path}")

def log_audit(session: Session, action: str, entity_type: str, entity_id: str, details: dict = None, user_id: str = "default_user"):
    audit = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        user_id=user_id,
        details=details or {}
    )
    session.add(audit)

def update_codebook_json(project_dir: Path, session: Session):
    """Update the codebook.json representation."""
    codes = session.query(Code).all()
    codebook_data = []
    for c in codes:
        codebook_data.append({
            "code_id": c.code_id,
            "name": c.name,
            "parent_code_id": c.parent_code_id,
            "definition": c.definition,
            "status": c.status
        })
    
    codebook_path = project_dir / "codebook" / "codebook.json"
    codebook_path.parent.mkdir(parents=True, exist_ok=True)
    with open(codebook_path, "w", encoding="utf-8") as f:
        json.dump(codebook_data, f, indent=2)

def create_code(project_dir: Path, name: str, parent_code_id: int = None, definition: str = None) -> int:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        code = Code(name=name, parent_code_id=parent_code_id, definition=definition)
        session.add(code)
        session.commit()
        session.refresh(code)
        
        log_audit(session, action="create", entity_type="Code", entity_id=str(code.code_id), 
                  details={"name": name, "parent_code_id": parent_code_id, "definition": definition})
        update_codebook_json(project_dir, session)
        session.commit()
        return code.code_id

def list_codes(project_dir: Path, show_all: bool = False) -> list:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        codes = session.query(Code).all()
        result = []
        for c in codes:
            status = c.status or "active"
            if not show_all:
                if status == "deprecated" or status.startswith("merged_into:") or status.startswith("split_into:"):
                    continue
            result.append({"code_id": c.code_id, "name": c.name, "parent_code_id": c.parent_code_id, "definition": c.definition, "status": status})
        return result

def apply_code(project_dir: Path, code_id: int, source_id: int, anchor: str, text_span: str = "", coder_id: str = "default_user") -> int:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        code = session.query(Code).filter_by(code_id=code_id).first()
        if not code:
            raise ValueError(f"Code with ID {code_id} not found")
        if code.status == "deprecated":
            raise ValueError(f"Code with ID {code_id} is deprecated and cannot be assigned")

        extract = session.query(Extract).filter_by(source_id=source_id, anchor=anchor).first()
        if not extract:
            extract = Extract(source_id=source_id, anchor=anchor, text_span=text_span)
            session.add(extract)
            session.commit()
            session.refresh(extract)
        
        assignment = CodeAssignment(
            extract_id=extract.extract_id,
            code_id=code_id,
            coder_id=coder_id,
            created_by=coder_id
        )
        session.add(assignment)
        session.commit()
        session.refresh(assignment)
        
        log_audit(session, action="apply", entity_type="CodeAssignment", entity_id=str(assignment.assignment_id), 
                  details={"code_id": code_id, "extract_id": extract.extract_id, "source_id": source_id, "anchor": anchor})
        session.commit()
        return assignment.assignment_id

def rename_code(project_dir: Path, code_id: int, new_name: str):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        code = session.query(Code).filter_by(code_id=code_id).first()
        if not code:
            raise ValueError(f"Code with ID {code_id} not found")
        old_name = code.name
        code.name = new_name
        
        log_audit(session, action="rename", entity_type="Code", entity_id=str(code.code_id), 
                  details={"old_name": old_name, "new_name": new_name})
        update_codebook_json(project_dir, session)
        session.commit()

def delete_code(project_dir: Path, code_id: int):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        code = session.query(Code).filter_by(code_id=code_id).first()
        if not code:
            raise ValueError(f"Code with ID {code_id} not found")
        
        code.status = "deprecated"
        
        log_audit(session, action="delete", entity_type="Code", entity_id=str(code.code_id), 
                  details={"status": "deprecated"})
        update_codebook_json(project_dir, session)
        session.commit()

def merge_codes(project_dir: Path, source_code_ids: list[int], target_code_name: str, definition: str = None) -> int:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        # Create the new merged code
        new_code = Code(name=target_code_name, definition=definition)
        session.add(new_code)
        session.commit()
        session.refresh(new_code)
        
        for code_id in source_code_ids:
            old_code = session.query(Code).filter_by(code_id=code_id).first()
            if old_code:
                old_code.status = f"merged_into:{new_code.code_id}"
                
                # Reassign code assignments to the new code
                assignments = session.query(CodeAssignment).filter_by(code_id=code_id).all()
                for assignment in assignments:
                    assignment.code_id = new_code.code_id

        log_audit(session, action="merge_codes", entity_type="Code", entity_id=str(new_code.code_id),
                  details={"source_code_ids": source_code_ids, "target_code_name": target_code_name})
        update_codebook_json(project_dir, session)
        session.commit()
        return new_code.code_id

def split_code(project_dir: Path, source_code_id: int, new_code_names: list[str]) -> list[int]:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        old_code = session.query(Code).filter_by(code_id=source_code_id).first()
        if not old_code:
            raise ValueError(f"Code with ID {source_code_id} not found")
            
        new_ids = []
        for name in new_code_names:
            new_code = Code(name=name)
            session.add(new_code)
            session.commit()
            session.refresh(new_code)
            new_ids.append(new_code.code_id)
            
        old_code.status = f"split_into:{new_ids}"
        
        # Mark current assignments as orphaned so they can be re-evaluated
        assignments = session.query(CodeAssignment).filter_by(code_id=source_code_id).all()
        for assignment in assignments:
            assignment.status = "orphaned"

        log_audit(session, action="split_code", entity_type="Code", entity_id=str(source_code_id),
                  details={"new_code_ids": new_ids, "new_code_names": new_code_names})
        update_codebook_json(project_dir, session)
        session.commit()
        return new_ids
