import random
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from typing import List

from models import Extract, CodeAssignment, Source

def get_db_engine(project_dir: Path):
    db_path = project_dir / "db" / "tt.sqlite"
    return create_engine(f"sqlite:///{db_path}")

def generate_irr_sample(project_dir: Path, source_id: int, percent: int) -> List[int]:
    """Generate a random sample of extracts for IRR double-coding."""
    if percent <= 0 or percent > 100:
        raise ValueError("Percent must be between 1 and 100")
        
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        source = session.query(Source).filter_by(source_id=source_id).first()
        if not source:
            raise ValueError(f"Source ID {source_id} not found.")
            
        extracts = session.query(Extract).filter_by(source_id=source_id).all()
        if not extracts:
            return []
            
        sample_size = max(1, int(len(extracts) * (percent / 100.0)))
        sampled_extracts = random.sample(extracts, sample_size)
        
        return [e.extract_id for e in sampled_extracts]

def calculate_cohen_kappa(project_dir: Path, coder_a: str, coder_b: str) -> float:
    """Calculate Cohen's Kappa between two coders across the project."""
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        assignments_a = session.query(CodeAssignment).filter_by(coder_id=coder_a).all()
        assignments_b = session.query(CodeAssignment).filter_by(coder_id=coder_b).all()
        
        extracts_a = {a.extract_id: a.code_id for a in assignments_a}
        extracts_b = {b.extract_id: b.code_id for b in assignments_b}
        
        common_extracts = set(extracts_a.keys()).intersection(set(extracts_b.keys()))
        
        if not common_extracts:
            raise ValueError(f"No commonly coded extracts found between '{coder_a}' and '{coder_b}'.")
            
        total_cases = len(common_extracts)
        agreements = 0
        
        codes_a_counts = {}
        codes_b_counts = {}
        
        for ext_id in common_extracts:
            c_a = extracts_a[ext_id]
            c_b = extracts_b[ext_id]
            
            if c_a == c_b:
                agreements += 1
                
            codes_a_counts[c_a] = codes_a_counts.get(c_a, 0) + 1
            codes_b_counts[c_b] = codes_b_counts.get(c_b, 0) + 1
            
        p0 = agreements / total_cases
        
        pe = 0.0
        all_codes = set(codes_a_counts.keys()).union(set(codes_b_counts.keys()))
        for code in all_codes:
            p_a = codes_a_counts.get(code, 0) / total_cases
            p_b = codes_b_counts.get(code, 0) / total_cases
            pe += p_a * p_b
            
        if pe == 1.0:
            return 1.0
            
        kappa = (p0 - pe) / (1.0 - pe)
        return kappa
