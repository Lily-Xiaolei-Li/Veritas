from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session

from models import Cluster, Theme, ClusterCode, ThemeCode, ThemeCluster
from code_manager import get_db_engine, log_audit

def create_cluster(project_dir: Path, name: str, description: Optional[str] = None) -> int:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        cluster = Cluster(name=name, description=description)
        session.add(cluster)
        session.commit()
        session.refresh(cluster)
        
        log_audit(session, action="create", entity_type="Cluster", entity_id=str(cluster.cluster_id),
                  details={"name": name, "description": description})
        session.commit()
        return cluster.cluster_id

def list_clusters(project_dir: Path) -> List[dict]:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        clusters = session.query(Cluster).all()
        return [{"cluster_id": c.cluster_id, "name": c.name, "description": c.description} for c in clusters]

def delete_cluster(project_dir: Path, cluster_id: int):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        cluster = session.query(Cluster).filter_by(cluster_id=cluster_id).first()
        if cluster:
            # delete mappings
            session.query(ClusterCode).filter_by(cluster_id=cluster_id).delete()
            session.query(ThemeCluster).filter_by(cluster_id=cluster_id).delete()
            session.delete(cluster)
            log_audit(session, action="delete", entity_type="Cluster", entity_id=str(cluster_id))
            session.commit()

def create_theme(project_dir: Path, name: str, description: Optional[str] = None, parent_theme_id: Optional[int] = None) -> int:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        theme = Theme(name=name, description=description, parent_theme_id=parent_theme_id)
        session.add(theme)
        session.commit()
        session.refresh(theme)
        
        log_audit(session, action="create", entity_type="Theme", entity_id=str(theme.theme_id),
                  details={"name": name, "description": description, "parent_theme_id": parent_theme_id})
        session.commit()
        return theme.theme_id

def list_themes(project_dir: Path) -> List[dict]:
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        themes = session.query(Theme).all()
        return [{"theme_id": t.theme_id, "name": t.name, "description": t.description, "parent_theme_id": t.parent_theme_id} for t in themes]

def delete_theme(project_dir: Path, theme_id: int):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        theme = session.query(Theme).filter_by(theme_id=theme_id).first()
        if theme:
            # delete mappings
            session.query(ThemeCode).filter_by(theme_id=theme_id).delete()
            session.query(ThemeCluster).filter_by(theme_id=theme_id).delete()
            session.delete(theme)
            log_audit(session, action="delete", entity_type="Theme", entity_id=str(theme_id))
            session.commit()

def assign_code_to_cluster(project_dir: Path, code_id: int, cluster_id: int):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        mapping = session.query(ClusterCode).filter_by(cluster_id=cluster_id, code_id=code_id).first()
        if not mapping:
            mapping = ClusterCode(cluster_id=cluster_id, code_id=code_id)
            session.add(mapping)
            log_audit(session, action="assign_code", entity_type="Cluster", entity_id=str(cluster_id),
                      details={"code_id": code_id})
            session.commit()

def unassign_code_from_cluster(project_dir: Path, code_id: int, cluster_id: int):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        mapping = session.query(ClusterCode).filter_by(cluster_id=cluster_id, code_id=code_id).first()
        if mapping:
            session.delete(mapping)
            log_audit(session, action="unassign_code", entity_type="Cluster", entity_id=str(cluster_id),
                      details={"code_id": code_id})
            session.commit()

def assign_code_to_theme(project_dir: Path, code_id: int, theme_id: int):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        mapping = session.query(ThemeCode).filter_by(theme_id=theme_id, code_id=code_id).first()
        if not mapping:
            mapping = ThemeCode(theme_id=theme_id, code_id=code_id)
            session.add(mapping)
            log_audit(session, action="assign_code", entity_type="Theme", entity_id=str(theme_id),
                      details={"code_id": code_id})
            session.commit()

def unassign_code_from_theme(project_dir: Path, code_id: int, theme_id: int):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        mapping = session.query(ThemeCode).filter_by(theme_id=theme_id, code_id=code_id).first()
        if mapping:
            session.delete(mapping)
            log_audit(session, action="unassign_code", entity_type="Theme", entity_id=str(theme_id),
                      details={"code_id": code_id})
            session.commit()

def assign_cluster_to_theme(project_dir: Path, cluster_id: int, theme_id: int):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        mapping = session.query(ThemeCluster).filter_by(theme_id=theme_id, cluster_id=cluster_id).first()
        if not mapping:
            mapping = ThemeCluster(theme_id=theme_id, cluster_id=cluster_id)
            session.add(mapping)
            log_audit(session, action="assign_cluster", entity_type="Theme", entity_id=str(theme_id),
                      details={"cluster_id": cluster_id})
            session.commit()

def unassign_cluster_from_theme(project_dir: Path, cluster_id: int, theme_id: int):
    engine = get_db_engine(project_dir)
    with Session(engine) as session:
        mapping = session.query(ThemeCluster).filter_by(theme_id=theme_id, cluster_id=cluster_id).first()
        if mapping:
            session.delete(mapping)
            log_audit(session, action="unassign_cluster", entity_type="Theme", entity_id=str(theme_id),
                      details={"cluster_id": cluster_id})
            session.commit()
