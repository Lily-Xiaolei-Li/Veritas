from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session

from models import JudgementNote, Extract
from code_manager import get_db_engine, log_audit

def tag_extract(
    project_dir: Path, 
    extract_id: int, 
    proposed_code_id: Optional[int] = None, 
    confidence: Optional[str] = None, 
    trigger_phrases: Optional[str] = None, 
    rationale: Optional[str] = None, 
    linked_rule: Optional[str] = None, 
    ladder_position: Optional[str] = None, 
    alternatives_considered: Optional[str] = None
) -> int:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        # Verify extract exists
        extract = session.query(Extract).filter_by(extract_id=extract_id).first()
        if not extract:
            raise ValueError(f"Extract with ID {extract_id} not found")

        note = JudgementNote(
            extract_id=extract_id,
            proposed_code_id=proposed_code_id,
            confidence=confidence,
            trigger_phrases=trigger_phrases,
            rationale=rationale,
            linked_rule=linked_rule,
            ladder_position=ladder_position,
            alternatives_considered=alternatives_considered
        )
        session.add(note)
        session.commit()
        session.refresh(note)
        
        log_audit(session, action="create", entity_type="JudgementNote", entity_id=str(note.note_id),
                  details={
                      "extract_id": extract_id,
                      "proposed_code_id": proposed_code_id,
                      "confidence": confidence
                  })
        session.commit()
        return note.note_id

def list_tags(project_dir: Path, extract_id: Optional[int] = None) -> List[dict]:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        query = session.query(JudgementNote)
        if extract_id is not None:
            query = query.filter_by(extract_id=extract_id)
        
        notes = query.all()
        return [{
            "note_id": n.note_id,
            "extract_id": n.extract_id,
            "proposed_code_id": n.proposed_code_id,
            "confidence": n.confidence,
            "trigger_phrases": n.trigger_phrases,
            "rationale": n.rationale,
            "linked_rule": n.linked_rule,
            "ladder_position": n.ladder_position,
            "alternatives_considered": n.alternatives_considered
        } for n in notes]
