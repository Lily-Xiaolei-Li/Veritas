import json
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from typing import Optional, Any, List

from models import Case, CaseAssignment, AuditLog
from code_manager import get_db_engine, log_audit

def create_case(project_dir: Path, name: str, description: Optional[str] = None, attributes: Optional[dict[str, Any]] = None) -> int:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        case = Case(name=name, description=description, attributes=attributes or {})
        session.add(case)
        session.commit()
        session.refresh(case)
        
        log_audit(session, action="create", entity_type="Case", entity_id=str(case.case_id),
                  details={"name": name, "description": description, "attributes": attributes})
        session.commit()
        return case.case_id

def list_cases(project_dir: Path) -> List[dict]:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        cases = session.query(Case).all()
        return [
            {
                "case_id": c.case_id,
                "name": c.name,
                "description": c.description,
                "attributes": c.attributes,
                "created_at": c.created_at.isoformat()
            } for c in cases
        ]

def delete_case(project_dir: Path, case_id: int):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        case = session.query(Case).filter_by(case_id=case_id).first()
        if not case:
            raise ValueError(f"Case {case_id} not found")
        
        session.delete(case)
        log_audit(session, action="delete", entity_type="Case", entity_id=str(case_id))
        session.commit()

def assign_case(project_dir: Path, case_id: int, source_id: Optional[int] = None, extract_id: Optional[int] = None, assigned_by: str = "user"):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        assignment = CaseAssignment(
            case_id=case_id,
            source_id=source_id,
            extract_id=extract_id,
            assigned_by=assigned_by
        )
        session.add(assignment)
        
        log_audit(session, action="assign_case", entity_type="CaseAssignment", entity_id=str(case_id),
                  details={"source_id": source_id, "extract_id": extract_id, "assigned_by": assigned_by})
        session.commit()
