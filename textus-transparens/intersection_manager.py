from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, and_
from typing import Optional, List, Any
from datetime import datetime

from models import CodeIntersection, Extract, Code, AuditLog
from code_manager import get_db_engine, log_audit

def add_intersection(project_dir: Path, extract_id: int, code_a_id: int, code_b_id: int, 
                     rel_type: str, rationale: str, is_ai: bool = False, reviewed_by: Optional[str] = None):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        # Check if codes exist
        ca = session.query(Code).filter_by(code_id=code_a_id).first()
        cb = session.query(Code).filter_by(code_id=code_b_id).first()
        if not ca or not cb:
            raise ValueError("One or both codes not found")
        
        intersection = CodeIntersection(
            extract_id=extract_id,
            code_a_id=code_a_id,
            code_b_id=code_b_id,
            relationship_type=rel_type,
            rationale=rationale,
            is_ai_generated=is_ai,
            reviewed_by=reviewed_by
        )
        session.add(intersection)
        
        log_audit(session, action="add_intersection", entity_type="CodeIntersection", 
                  entity_id=f"{code_a_id}-{code_b_id}",
                  details={"extract_id": extract_id, "type": rel_type, "is_ai": is_ai})
        session.commit()

def list_intersections(project_dir: Path, extract_id: Optional[int] = None) -> List[dict]:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        query = session.query(CodeIntersection)
        if extract_id:
            query = query.filter_by(extract_id=extract_id)
        
        intersections = query.all()
        return [
            {
                "id": i.intersection_id,
                "extract_id": i.extract_id,
                "code_a": i.code_a.name,
                "code_b": i.code_b.name,
                "type": i.relationship_type,
                "rationale": i.rationale,
                "is_ai": i.is_ai_generated,
                "reviewed_by": i.reviewed_by
            } for i in intersections
        ]
