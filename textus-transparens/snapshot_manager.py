import os
import zipfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

def create_snapshot(project_dir: Path, description: str = "") -> str:
    """Zip the current database (tt.sqlite) and all 'canonical' markdown/meta/map files."""
    snapshots_dir = project_dir / "snapshots"
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snapshot_name = f"snapshot_{timestamp}.zip"
    snapshot_path = snapshots_dir / snapshot_name
    
    db_path = project_dir / "db" / "tt.sqlite"
    sources_dir = project_dir / "sources"
    
    with zipfile.ZipFile(snapshot_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if db_path.exists():
            zipf.write(db_path, "db/tt.sqlite")
        
        if sources_dir.exists():
            for source_dir in sources_dir.iterdir():
                if source_dir.is_dir():
                    canonical_dir = source_dir / "canonical"
                    if canonical_dir.exists():
                        for file_path in canonical_dir.iterdir():
                            if file_path.is_file():
                                arcname = f"sources/{source_dir.name}/canonical/{file_path.name}"
                                zipf.write(file_path, arcname)
                                
        # Optional: store metadata about the snapshot
        meta_content = f"description: {description}\ntimestamp: {timestamp}\n"
        zipf.writestr("snapshot_meta.yaml", meta_content)
        
    return snapshot_name

def restore_snapshot(project_dir: Path, snapshot_name: str) -> str:
    """Extract a specific snapshot zip, replacing the current DB and canonical files.
    Returns the path to the backup created before restoration."""
    snapshot_path = project_dir / "snapshots" / snapshot_name
    if not snapshot_path.exists():
        raise FileNotFoundError(f"Snapshot '{snapshot_name}' not found.")
        
    # Backup current state before restoring
    backup_timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = project_dir / "snapshots" / f"backup_before_restore_{backup_timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    db_path = project_dir / "db" / "tt.sqlite"
    if db_path.exists():
        (backup_dir / "db").mkdir(parents=True, exist_ok=True)
        shutil.copy2(db_path, backup_dir / "db" / "tt.sqlite")
        
    sources_dir = project_dir / "sources"
    if sources_dir.exists():
        shutil.copytree(sources_dir, backup_dir / "sources", dirs_exist_ok=True)
        
    # Extract the snapshot
    with zipfile.ZipFile(snapshot_path, 'r') as zipf:
        # Extract over the existing project dir
        for member in zipf.namelist():
            if member.startswith("db/") or member.startswith("sources/"):
                zipf.extract(member, project_dir)
                
    return str(backup_dir)
