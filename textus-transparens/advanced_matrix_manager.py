from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, joinedload

from models import (
    CodeAssignment, Theme, Cluster, Case, 
    ThemeCode, ClusterCode, CaseAssignment as DbCaseAssignment
)

def get_db_engine(project_dir: Path):
    db_path = project_dir / "db" / "tt.sqlite"
    return create_engine(f"sqlite:///{db_path}")

def build_advanced_matrix(project_dir: Path, x_axis: str, y_axis: str) -> Dict[str, Any]:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        # Load all code assignments with their associated extracts
        assignments = session.query(CodeAssignment).options(
            joinedload(CodeAssignment.extract)
        ).all()
        
        # Build mapping for themes
        code_to_themes = defaultdict(list)
        for tc, theme in session.query(ThemeCode, Theme).filter(ThemeCode.theme_id == Theme.theme_id).all():
            code_to_themes[tc.code_id].append(theme.name)
            
        # Build mapping for clusters
        code_to_clusters = defaultdict(list)
        for cc, cluster in session.query(ClusterCode, Cluster).filter(ClusterCode.cluster_id == Cluster.cluster_id).all():
            code_to_clusters[cc.code_id].append(cluster.name)
            
        # Build mappings for cases (via extracts or sources)
        source_to_cases = defaultdict(list)
        extract_to_cases = defaultdict(list)
        for ca, case_obj in session.query(DbCaseAssignment, Case).filter(DbCaseAssignment.case_id == Case.case_id).all():
            if ca.extract_id:
                extract_to_cases[ca.extract_id].append(case_obj)
            if ca.source_id:
                source_to_cases[ca.source_id].append(case_obj)

        def get_axis_values(axis: str, assignment: CodeAssignment) -> List[str]:
            if axis == 'theme':
                return code_to_themes.get(assignment.code_id, ["Uncategorized"]) or ["Uncategorized"]
            elif axis == 'cluster':
                return code_to_clusters.get(assignment.code_id, ["Uncategorized"]) or ["Uncategorized"]
            elif axis == 'case' or axis.startswith('case_attr:'):
                cases = []
                if assignment.extract_id:
                    cases = extract_to_cases.get(assignment.extract_id, [])
                if not cases and assignment.extract and assignment.extract.source_id:
                    cases = source_to_cases.get(assignment.extract.source_id, [])
                
                if not cases:
                    return ["Unassigned"]
                    
                if axis == 'case':
                    return [c.name for c in cases]
                else:
                    attr_key = axis.split(':', 1)[1]
                    vals = []
                    for c in cases:
                        val = c.attributes.get(attr_key) if c.attributes else None
                        vals.append(str(val) if val is not None else "Unknown")
                    return vals
            return ["Unknown"]

        # Matrix format: matrix[x][y] = {"density": int, "sources": set, "quotes": list}
        matrix_data = defaultdict(lambda: defaultdict(lambda: {
            "density": 0,
            "sources": set(),
            "quotes": []
        }))
        
        x_labels = set()
        y_labels = set()
        
        for assignment in assignments:
            x_vals = get_axis_values(x_axis, assignment)
            y_vals = get_axis_values(y_axis, assignment)
            
            source_id = assignment.extract.source_id if assignment.extract else None
            quote = assignment.extract.text_span if assignment.extract else ""
            
            for xv in x_vals:
                x_labels.add(xv)
                for yv in y_vals:
                    y_labels.add(yv)
                    cell = matrix_data[xv][yv]
                    
                    cell["density"] += 1
                    if source_id is not None:
                        cell["sources"].add(source_id)
                    if quote and len(cell["quotes"]) < 3:
                        cell["quotes"].append(quote)
                        
        # Construct the final structure suitable for Rich table displays
        result = {
            "x_axis_name": x_axis,
            "y_axis_name": y_axis,
            "x_labels": sorted(list(x_labels)),
            "y_labels": sorted(list(y_labels)),
            "matrix": {}
        }
        
        for xv in result["x_labels"]:
            result["matrix"][xv] = {}
            for yv in result["y_labels"]:
                cell = matrix_data[xv][yv]
                result["matrix"][xv][yv] = {
                    "density": cell["density"],
                    "breadth": len(cell["sources"]),
                    "quotes": cell["quotes"]
                }
                
        return result