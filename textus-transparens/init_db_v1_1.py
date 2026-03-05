import sys
from pathlib import Path
from sqlalchemy import create_engine
from models import Base

def init_v1_1_tables(project_dir: Path):
    db_path = project_dir / "db" / "tt.sqlite"
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return
    
    engine = create_engine(f"sqlite:///{db_path}")
    print(f"Initializing new tables for v1.1 in {db_path}...")
    
    # This will only create tables that don't exist yet
    Base.metadata.create_all(engine)
    print("Success: New tables created (if they didn't exist).")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python init_db_v1_1.py <project_dir>")
        sys.exit(1)
    
    project_path = Path(sys.argv[1])
    init_v1_1_tables(project_path)
