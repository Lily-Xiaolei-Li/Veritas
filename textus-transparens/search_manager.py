import os
import re
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from models import Source, Code, CodeAssignment, Extract, AuditLog

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

def setup_fts(project_dir: Path):
    engine = get_db_engine(project_dir)
    with engine.begin() as conn:
        conn.execute(text('''
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_content USING fts5(
                source_id,
                content
            )
        '''))

def index_source(project_dir: Path, source_id_str: str, content: str):
    engine = get_db_engine(project_dir)
    with engine.begin() as conn:
        # Delete existing entries for this source just in case
        conn.execute(text('DELETE FROM fts_content WHERE source_id = :source_id'), {"source_id": source_id_str})
        conn.execute(text('INSERT INTO fts_content (source_id, content) VALUES (:source_id, :content)'), 
                     {"source_id": source_id_str, "content": content})

def search_text(project_dir: Path, query: str):
    engine = get_db_engine(project_dir)
    matches = []
    
    setup_fts(project_dir) # Ensure table exists just in case
    
    with Session(engine) as session:
        # Perform FTS5 query
        # Use snippet function provided by FTS5
        sql = text('''
            SELECT source_id, snippet(fts_content, 1, '[bold red]', '[/bold red]', '...', 64) as snip
            FROM fts_content 
            WHERE fts_content MATCH :query
        ''')
        
        # Format the query for FTS5 exact phrase search if needed
        escaped_query = f'"{query}"' if ' ' in query and not query.startswith('"') else query
        
        try:
            results = session.execute(sql, {"query": escaped_query}).fetchall()
            for row in results:
                source_id_str = row.source_id
                snippet = row.snip
                md_path = project_dir / "sources" / source_id_str / "canonical" / "source.md"
                matches.append({
                    "source_id": source_id_str,
                    "snippet": snippet,
                    "file_path": str(md_path.relative_to(project_dir)) if md_path.exists() else f"sources/{source_id_str}/canonical/source.md"
                })
        except Exception as e:
            # Fallback if FTS5 query fails (e.g., due to special characters)
            pass
        
        log_audit(session, action="search_text", entity_type="System", entity_id="", details={"query": query})
        session.commit()
    return matches

def search_by_code(project_dir: Path, code_id: int):
    engine = get_db_engine(project_dir)
    results = []
    with Session(engine) as session:
        code = session.query(Code).filter_by(code_id=code_id).first()
        if not code:
            raise ValueError(f"Code with ID {code_id} not found")
            
        assignments = session.query(CodeAssignment).filter_by(code_id=code_id).all()
        for assignment in assignments:
            extract = assignment.extract
            source = extract.source
            source_id_str = f"S{source.source_id:04d}"
            results.append({
                "assignment_id": assignment.assignment_id,
                "source_id": source_id_str,
                "anchor": extract.anchor,
                "text_span": extract.text_span
            })
        
        log_audit(session, action="search_code", entity_type="Code", entity_id=str(code_id), details={})
        session.commit()
    return results

def search_cross(project_dir: Path, code_a_id: int, code_b_id: int):
    engine = get_db_engine(project_dir)
    results = []
    with Session(engine) as session:
        sources_a = {a.extract.source_id for a in session.query(CodeAssignment).filter_by(code_id=code_a_id).all()}
        sources_b = {a.extract.source_id for a in session.query(CodeAssignment).filter_by(code_id=code_b_id).all()}
        
        common_source_ids = sources_a.intersection(sources_b)
        
        for s_id in common_source_ids:
            source = session.query(Source).filter_by(source_id=s_id).first()
            if source:
                source_id_str = f"S{source.source_id:04d}"
                results.append({
                    "source_id": source_id_str,
                    "type": source.source_type
                })
        
        log_audit(session, action="search_cross", entity_type="System", entity_id="", details={"code_a": code_a_id, "code_b": code_b_id})
        session.commit()
    return results

def reindex_project(project_dir: Path):
    engine = get_db_engine(project_dir)
    setup_fts(project_dir)
    with Session(engine) as session:
        session.execute(text('DELETE FROM fts_content'))
        
        sources = session.query(Source).all()
        for source in sources:
            source_id_str = f"S{source.source_id:04d}"
            md_path = project_dir / "sources" / source_id_str / "canonical" / "source.md"
            if md_path.exists():
                try:
                    with open(md_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    session.execute(text('INSERT INTO fts_content (source_id, content) VALUES (:source_id, :content)'), 
                                 {"source_id": source_id_str, "content": content})
                except Exception as e:
                    pass # Silently skip unreadable files or log them
        
        log_audit(session, action="reindex_project", entity_type="System", entity_id="", details={})
        session.commit()

