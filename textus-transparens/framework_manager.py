import json
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from typing import Optional, List, Any
from datetime import datetime

from models import TheoreticalFramework, FrameworkDimension, AuditLog
from code_manager import get_db_engine, log_audit

def create_framework(project_dir: Path, name: str, description: Optional[str] = None) -> int:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        framework = TheoreticalFramework(name=name, description=description)
        session.add(framework)
        session.commit()
        session.refresh(framework)
        
        log_audit(session, action="create_framework", entity_type="TheoreticalFramework", entity_id=str(framework.framework_id),
                  details={"name": name, "description": description})
        session.commit()
        return framework.framework_id

def add_dimension(project_dir: Path, framework_id: int, name: str, definition: str, mapped_code_id: Optional[int] = None) -> int:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        dimension = FrameworkDimension(
            framework_id=framework_id,
            name=name,
            definition=definition,
            mapped_code_id=mapped_code_id
        )
        session.add(dimension)
        session.commit()
        session.refresh(dimension)
        
        log_audit(session, action="add_dimension", entity_type="FrameworkDimension", entity_id=str(dimension.dimension_id),
                  details={"name": name, "framework_id": framework_id, "mapped_code_id": mapped_code_id})
        session.commit()
        return dimension.dimension_id

def list_frameworks(project_dir: Path) -> List[dict]:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        frameworks = session.query(TheoreticalFramework).all()
        return [
            {
                "id": f.framework_id,
                "name": f.name,
                "description": f.description,
                "dimensions_count": len(f.dimensions)
            } for f in frameworks
        ]

def get_framework_details(project_dir: Path, framework_id: int) -> Optional[dict]:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        f = session.query(TheoreticalFramework).filter_by(framework_id=framework_id).first()
        if not f:
            return None
        
        return {
            "id": f.framework_id,
            "name": f.name,
            "description": f.description,
            "dimensions": [
                {
                    "id": d.dimension_id,
                    "name": d.name,
                    "definition": d.definition,
                    "mapped_code_id": d.mapped_code_id
                } for d in f.dimensions
            ]
        }

def delete_framework(project_dir: Path, framework_id: int):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        f = session.query(TheoreticalFramework).filter_by(framework_id=framework_id).first()
        if not f:
            raise ValueError(f"Framework {framework_id} not found")
        
        session.delete(f)
        log_audit(session, action="delete_framework", entity_type="TheoreticalFramework", entity_id=str(framework_id))
        session.commit()
