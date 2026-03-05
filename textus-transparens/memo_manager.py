import json
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from typing import Optional

from models import Memo, AuditLog
from code_manager import get_db_engine, log_audit

def create_memo(
    project_dir: Path,
    memo_type: str,
    text: str,
    source_id: Optional[int] = None,
    extract_id: Optional[int] = None,
    code_id: Optional[int] = None,
    theme_id: Optional[int] = None,
    case_id: Optional[int] = None
) -> int:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        memo = Memo(
            type=memo_type,
            text=text,
            source_id=source_id,
            extract_id=extract_id,
            code_id=code_id,
            theme_id=theme_id,
            case_id=case_id
        )
        session.add(memo)
        session.commit()
        session.refresh(memo)
        
        log_audit(session, action="create", entity_type="Memo", entity_id=str(memo.memo_id),
                  details={
                      "type": memo_type,
                      "source_id": source_id,
                      "extract_id": extract_id,
                      "code_id": code_id,
                      "theme_id": theme_id,
                      "case_id": case_id
                  })
        session.commit()
        return memo.memo_id

def list_memos(project_dir: Path) -> list[dict]:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        memos = session.query(Memo).all()
        return [
            {
                "memo_id": m.memo_id,
                "type": m.type,
                "text": m.text,
                "source_id": m.source_id,
                "extract_id": m.extract_id,
                "code_id": m.code_id,
                "theme_id": m.theme_id,
                "case_id": m.case_id,
                "created_at": m.created_at.isoformat()
            } for m in memos
        ]

def delete_memo(project_dir: Path, memo_id: int):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        memo = session.query(Memo).filter_by(memo_id=memo_id).first()
        if not memo:
            raise ValueError(f"Memo {memo_id} not found")
        
        session.delete(memo)
        log_audit(session, action="delete", entity_type="Memo", entity_id=str(memo_id))
        session.commit()
