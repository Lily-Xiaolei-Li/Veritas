import os
import re
import uuid
import json
import subprocess
import requests
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from models import Code, Source, AISuggestion, Project, Extract, CodeAssignment, AuditLog
from code_manager import get_db_engine, log_audit, apply_code

def extract_json_array(text: str) -> list[dict]:
    # Remove <think>...</think> blocks if present
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = text.strip()
    
    if not text:
        return []

    def try_parse(json_str: str):
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Strategy C: clean trailing commas
            cleaned = re.sub(r',\s*]', ']', json_str)
            cleaned = re.sub(r',\s*}', '}', cleaned)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return None

    # Strategy B: code blocks
    code_blocks = re.findall(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    for block in code_blocks:
        parsed = try_parse(block)
        if parsed is not None and isinstance(parsed, list):
            return parsed

    # Strategy A: first '[' and last ']'
    first_bracket = text.find('[')
    last_bracket = text.rfind(']')
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        json_str = text[first_bracket:last_bracket+1]
        parsed = try_parse(json_str)
        if parsed is not None and isinstance(parsed, list):
            return parsed

    # Direct parse
    parsed = try_parse(text)
    if parsed is not None and isinstance(parsed, list):
        return parsed

    return []

class AIBackend:
    def suggest(self, text: str, code_name: str, code_def: str, inclusion_rules: str, model_name: str) -> list[dict]:
        raise NotImplementedError

class GeminiAPIBackend(AIBackend):
    def suggest(self, text: str, code_name: str, code_def: str, inclusion_rules: str, model_name: str) -> list[dict]:
        prompt = (
            f"Analyze the following text and find spans that match the code '{code_name}'.\n"
            f"Code Definition: {code_def}\n"
            f"Inclusion Rules: {inclusion_rules}\n\n"
            f"Return ONLY a JSON array of objects with keys 'span' (the exact text snippet) and 'rationale' (why it matches). Do not include any markdown formatting, backticks, or explanation. Text:\n"
            f"{text[:5000]}"
        )
        try:
            result = subprocess.run(
                ['gemini', '-m', model_name, '-p', prompt, '--approval-mode', 'yolo'],
                capture_output=True,
                text=True,
                shell=True
            )
            text_response = result.stdout.strip()
            return extract_json_array(text_response)
        except Exception as e:
            return [{"span": f"Error span", "rationale": f"CLI call failed: {e}. Output was: {text_response[:200] if 'text_response' in locals() else ''}..."}]

class LocalOllamaBackend(AIBackend):
    def suggest(self, text: str, code_name: str, code_def: str, inclusion_rules: str, model_name: str) -> list[dict]:
        prompt = (
            f"Analyze the following text and find spans that match the code '{code_name}'.\n"
            f"Code Definition: {code_def}\n"
            f"Inclusion Rules: {inclusion_rules}\n\n"
            f"Return ONLY a JSON array of objects with keys 'span' (the exact text snippet) and 'rationale' (why it matches). Do not include any markdown formatting, backticks, or explanation. Text:\n"
            f"{text[:5000]}"
        )
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            text_response = response.json().get("response", "")
            return extract_json_array(text_response)
        except Exception as e:
            return [{"span": f"Error span", "rationale": f"Ollama call failed: {e}. Output was: {text_response[:200] if 'text_response' in locals() else ''}..."}]

class BackendRegistry:
    def __init__(self):
        self.backends = {
            "gemini": GeminiAPIBackend(),
            "ollama": LocalOllamaBackend()
        }
    
    def get(self, name: str) -> AIBackend:
        return self.backends.get(name, self.backends["gemini"])

registry = BackendRegistry()

def generate_suggestions(project_dir: Path, source_id_str: str, code_id: int, provider: str = "gemini", model: str = "flash"):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        code = session.query(Code).filter_by(code_id=code_id).first()
        if not code:
            raise ValueError(f"Code {code_id} not found.")
        
        # Parse source ID (e.g. S0001 -> 1, or just int)
        try:
            source_int = int(source_id_str.lstrip('S0')) if str(source_id_str).startswith('S') else int(source_id_str)
        except ValueError:
            source_int = int(source_id_str)

        source = session.query(Source).filter_by(source_id=source_int).first()
        if not source:
            raise ValueError(f"Source {source_id_str} not found.")
        
        # Determine canonical path
        # Reconstruct S0001 format
        source_dir_name = f"S{source_int:04d}"
        md_path = project_dir / "sources" / source_dir_name / "canonical" / "source.md"
        if not md_path.exists():
            raise FileNotFoundError(f"Canonical MD for {source_dir_name} not found at {md_path}.")
        
        with open(md_path, "r", encoding="utf-8") as f:
            text = f.read()

        backend = registry.get(provider)
        suggestions = backend.suggest(text, code.name, code.definition or "", code.inclusion_rules or "", model)
        
        run_id = str(uuid.uuid4())
        count = 0
        for sug in suggestions:
            record = AISuggestion(
                run_id=run_id,
                source_id=source.source_id,
                suggested_code_id=code.code_id,
                suggested_span=sug.get("span", ""),
                rationale=sug.get("rationale", ""),
                status="pending"
            )
            session.add(record)
            count += 1
            
        log_audit(session, action="ai_suggest", entity_type="AISuggestion", entity_id=run_id, 
                  details={"source_id": source.source_id, "code_id": code.code_id, "count": count})
        session.commit()
        return count

def list_suggestions(project_dir: Path, status: str = "pending"):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        suggestions = session.query(AISuggestion).filter_by(status=status).all()
        return [{
            "id": s.suggestion_id,
            "source_id": s.source_id,
            "code_id": s.suggested_code_id,
            "span": s.suggested_span,
            "rationale": s.rationale,
            "status": s.status
        } for s in suggestions]

def review_suggestion(project_dir: Path, suggestion_id: int, action: str, reason: str = ""):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        suggestion = session.query(AISuggestion).filter_by(suggestion_id=suggestion_id).first()
        if not suggestion:
            raise ValueError(f"Suggestion {suggestion_id} not found.")
        
        if action == "accept":
            suggestion.status = "accepted"
            suggestion.decision_reason = reason
            
            # Create Extract and CodeAssignment
            # For MVP, anchor is a dummy one or first 20 chars of span
            anchor = f"ai_span:{suggestion.suggested_span[:20]}" 
            extract = Extract(source_id=suggestion.source_id, anchor=anchor, text_span=suggestion.suggested_span)
            session.add(extract)
            session.commit()
            session.refresh(extract)
            
            assignment = CodeAssignment(
                extract_id=extract.extract_id,
                code_id=suggestion.suggested_code_id,
                coder_id="ai_assisted_user",
                created_by="ai_assisted_user"
            )
            session.add(assignment)
            
            log_audit(session, action="review_accept", entity_type="AISuggestion", entity_id=str(suggestion_id), 
                      details={"assignment_id": assignment.assignment_id, "reason": reason})
        
        elif action == "reject":
            suggestion.status = "rejected"
            suggestion.decision_reason = reason
            log_audit(session, action="review_reject", entity_type="AISuggestion", entity_id=str(suggestion_id), 
                      details={"reason": reason})
        else:
            raise ValueError("Action must be 'accept' or 'reject'")
            
        session.commit()