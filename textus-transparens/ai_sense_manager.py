import subprocess
import requests
from pathlib import Path
from sqlalchemy.orm import Session
from models import TheoreticalFramework, FrameworkDimension, Extract, CodeIntersection
from code_manager import get_db_engine, log_audit
from ai_manager import extract_json_array

def perform_ai_sense(project_dir, framework_id, source_id=None, provider='gemini', model='pro'):
    if isinstance(project_dir, str):
        project_dir = Path(project_dir)
        
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        framework = session.query(TheoreticalFramework).filter_by(framework_id=framework_id).first()
        if not framework:
            raise ValueError(f"Framework {framework_id} not found.")
        
        dimensions = session.query(FrameworkDimension).filter_by(framework_id=framework_id).all()
        if not dimensions:
            return 0
            
        valid_dims = [d for d in dimensions if d.mapped_code_id is not None]
        if not valid_dims:
            return 0
            
        dim_map = {d.name: d.mapped_code_id for d in valid_dims}
        dim_descriptions = "\n".join([f"- {d.name}: {d.definition}" for d in valid_dims])
        
        query = session.query(Extract)
        if source_id is not None:
            query = query.filter_by(source_id=source_id)
        extracts = query.all()
        
        total_intersections = 0
        
        for ext in extracts:
            prompt = (
                f"Analyze the following text extract and identify any 'tensions' or 'overlaps' "
                f"between the provided theoretical framework dimensions.\n\n"
                f"Framework Dimensions:\n{dim_descriptions}\n\n"
                f"Extract text:\n{ext.text_span}\n\n"
                f"Return ONLY a JSON array of objects with keys: "
                f"'dimension_a' (exact name of the first dimension), "
                f"'dimension_b' (exact name of the second dimension), "
                f"'relationship_type' (either 'tension' or 'overlap'), "
                f"'rationale' (detailed explanation of the relationship based on the text).\n"
                f"Do not include any markdown formatting, backticks, or explanation."
            )
            
            text_response = ""
            if provider == 'gemini':
                try:
                    result = subprocess.run(
                        ['gemini', '-m', model, '-p', prompt, '--approval-mode', 'yolo'],
                        capture_output=True,
                        text=True,
                        shell=True
                    )
                    text_response = result.stdout.strip()
                except Exception as e:
                    continue
            elif provider == 'ollama':
                try:
                    response = requests.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": model,
                            "prompt": prompt,
                            "stream": False
                        }
                    )
                    response.raise_for_status()
                    text_response = response.json().get("response", "")
                except Exception as e:
                    continue
            else:
                raise ValueError(f"Unknown provider: {provider}")
                
            results = extract_json_array(text_response)
            
            for item in results:
                dim_a = item.get("dimension_a")
                dim_b = item.get("dimension_b")
                rel_type = item.get("relationship_type")
                rationale = item.get("rationale")
                
                if not dim_a or not dim_b or not rel_type or not rationale:
                    continue
                    
                code_a_id = dim_map.get(dim_a)
                code_b_id = dim_map.get(dim_b)
                
                if code_a_id and code_b_id and code_a_id != code_b_id:
                    intersection = CodeIntersection(
                        extract_id=ext.extract_id,
                        code_a_id=code_a_id,
                        code_b_id=code_b_id,
                        relationship_type=rel_type,
                        rationale=rationale,
                        is_ai_generated=True
                    )
                    session.add(intersection)
                    total_intersections += 1
        
        log_audit(
            session, 
            action="ai_sense", 
            entity_type="TheoreticalFramework", 
            entity_id=str(framework_id), 
            details={
                "source_id": source_id, 
                "intersections_found": total_intersections, 
                "provider": provider, 
                "model": model
            }
        )
        session.commit()
        return total_intersections