import subprocess
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import Session
from pathlib import Path

from models import AuditLog, Memo, JudgementNote
from code_manager import get_db_engine

def synthesize_evolution(project_dir: Path, start_date: Optional[datetime] = None) -> str:
    """
    Synthesizes the qualitative research evolution narrative by querying 
    AuditLog, Memo, and JudgementNote tables, formatting them chronologically,
    and passing them to the Gemini CLI.
    """
    engine = get_db_engine(project_dir)
    entries = []
    
    with Session(engine) as session:
        # Query AuditLogs
        audit_stmt = select(AuditLog)
        if start_date:
            audit_stmt = audit_stmt.where(AuditLog.created_at >= start_date)
        for log in session.execute(audit_stmt).scalars():
            entries.append({
                "type": "Audit",
                "id": log.log_id,
                "created_at": log.created_at,
                "content": f"{log.action} on {log.entity_type} ({log.entity_id}): {log.details}"
            })
            
        # Query Memos
        memo_stmt = select(Memo)
        if start_date:
            memo_stmt = memo_stmt.where(Memo.created_at >= start_date)
        for memo in session.execute(memo_stmt).scalars():
            entries.append({
                "type": "Memo",
                "id": memo.memo_id,
                "created_at": memo.created_at,
                "content": f"[{memo.type}] {memo.text}"
            })
            
        # Query JudgementNotes
        judgement_stmt = select(JudgementNote)
        if start_date:
            judgement_stmt = judgement_stmt.where(JudgementNote.created_at >= start_date)
        for note in session.execute(judgement_stmt).scalars():
            entries.append({
                "type": "Judgement",
                "id": note.note_id,
                "created_at": note.created_at,
                "content": f"Confidence: {note.confidence} | Rationale: {note.rationale} | Phrases: {note.trigger_phrases}"
            })
            
    # Sort all entries chronologically
    entries.sort(key=lambda x: x["created_at"])
    
    if not entries:
        return "No narrative to synthesize: no logs, memos, or judgement notes found."
    
    # Format chronological history string
    history_lines = []
    for entry in entries:
        date_str = entry["created_at"].isoformat() if hasattr(entry["created_at"], "isoformat") else str(entry["created_at"])
        history_lines.append(f"[{entry['type']}-{entry['id']}] {date_str} - {entry['content']}")
        
    history_text = "\n".join(history_lines)
    
    # Construct the prompt for Gemini
    prompt = (
        "You are an expert qualitative researcher. Synthesize the following chronological history "
        "of project logs, memos, and judgement notes into a cohesive qualitative research evolution narrative.\n\n"
        "Explain structural shifts in the research, key theoretical breakthroughs, and how 'gut feelings' or specific "
        "observations led to changes in the codebook or thematic structure.\n\n"
        "CRITICAL INSTRUCTION: You MUST cite the source of your synthesis using the exact provided IDs "
        "(e.g., [Audit-12], [Memo-5], [Judgement-3]) for traceability. Do not hallucinate IDs.\n\n"
        "Return the final synthesized narrative in Markdown format.\n\n"
        "### Project History ###\n"
        f"{history_text}\n"
    )
    
    # Call Gemini CLI
    try:
        result = subprocess.run(
            ["gemini.cmd", "-m", "pro", "--approval-mode", "yolo"],
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=True,
            check=True
        )
        output = result.stdout.strip()
        # Clean up any potential code block wrapping if Gemini decides to be helpful
        if output.startswith("```markdown"):
            output = output.split("```markdown")[1].split("```")[0].strip()
        elif output.startswith("```"):
            output = output.split("```")[1].split("```")[0].strip()
        return output
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to generate narrative via Gemini CLI: {e.stderr}") from e
