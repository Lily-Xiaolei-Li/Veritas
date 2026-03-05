from datetime import datetime, timezone
from typing import Optional, List, Any
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"
    
    project_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    
    sources: Mapped[List["Source"]] = relationship(back_populates="project")

class Source(Base):
    __tablename__ = "sources"
    
    source_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.project_id"))
    source_type: Mapped[str] = mapped_column(String(50))
    source_uri: Mapped[str] = mapped_column(String(1024))
    original_hash: Mapped[Optional[str]] = mapped_column(String(255))
    canonical_md_hash: Mapped[Optional[str]] = mapped_column(String(255))
    map_hash: Mapped[Optional[str]] = mapped_column(String(255))
    canonical_md_version_id: Mapped[Optional[str]] = mapped_column(String(255))
    conversion_provenance: Mapped[Optional[str]] = mapped_column(Text)
    attributes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    
    project: Mapped["Project"] = relationship(back_populates="sources")
    extracts: Mapped[List["Extract"]] = relationship(back_populates="source")
    case_assignments: Mapped[List["CaseAssignment"]] = relationship(back_populates="source")

class Extract(Base):
    __tablename__ = "extracts"
    
    extract_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.source_id"))
    anchor: Mapped[str] = mapped_column(String(512)) # e.g., p:12|h:Methods>Audit trail|b:07
    text_span: Mapped[str] = mapped_column(Text)
    snapshot: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    
    source: Mapped["Source"] = relationship(back_populates="extracts")
    assignments: Mapped[List["CodeAssignment"]] = relationship(back_populates="extract")
    intersections: Mapped[List["CodeIntersection"]] = relationship(back_populates="extract")
    case_assignments: Mapped[List["CaseAssignment"]] = relationship(back_populates="extract")

class Code(Base):
    __tablename__ = "codes"
    
    code_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    parent_code_id: Mapped[Optional[int]] = mapped_column(ForeignKey("codes.code_id"))
    definition: Mapped[Optional[str]] = mapped_column(Text)
    inclusion_rules: Mapped[Optional[str]] = mapped_column(Text)
    exclusion_rules: Mapped[Optional[str]] = mapped_column(Text)
    boundary_rules: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="active") # active, deprecated, merged_into:<id>, split_into:[<id>,...]
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    
    assignments: Mapped[List["CodeAssignment"]] = relationship(back_populates="code")
    children: Mapped[List["Code"]] = relationship("Code", back_populates="parent", remote_side=[code_id])
    parent: Mapped[Optional["Code"]] = relationship("Code", back_populates="children", remote_side=[parent_code_id])
    framework_dimensions: Mapped[List["FrameworkDimension"]] = relationship(back_populates="mapped_code")

class CodeAssignment(Base):
    __tablename__ = "code_assignments"
    
    assignment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    extract_id: Mapped[int] = mapped_column(ForeignKey("extracts.extract_id"))
    code_id: Mapped[int] = mapped_column(ForeignKey("codes.code_id"))
    coder_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    created_by: Mapped[str] = mapped_column(String(100))
    anchor_resolved_at_version: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="active") # active/orphaned
    
    extract: Mapped["Extract"] = relationship(back_populates="assignments")
    code: Mapped["Code"] = relationship(back_populates="assignments")

class Memo(Base):
    __tablename__ = "memos"
    
    memo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text)
    source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sources.source_id"))
    extract_id: Mapped[Optional[int]] = mapped_column(ForeignKey("extracts.extract_id"))
    code_id: Mapped[Optional[int]] = mapped_column(ForeignKey("codes.code_id"))
    theme_id: Mapped[Optional[int]] = mapped_column(ForeignKey("themes.theme_id"))
    case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cases.case_id"))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class Cluster(Base):
    __tablename__ = "clusters"
    
    cluster_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

class Theme(Base):
    __tablename__ = "themes"
    
    theme_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    parent_theme_id: Mapped[Optional[int]] = mapped_column(ForeignKey("themes.theme_id"))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

class ClusterCode(Base):
    __tablename__ = "cluster_codes"
    
    mapping_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.cluster_id"))
    code_id: Mapped[int] = mapped_column(ForeignKey("codes.code_id"))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

class ThemeCode(Base):
    __tablename__ = "theme_codes"
    
    mapping_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(ForeignKey("themes.theme_id"))
    code_id: Mapped[int] = mapped_column(ForeignKey("codes.code_id"))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

class ThemeCluster(Base):
    __tablename__ = "theme_clusters"
    
    mapping_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    theme_id: Mapped[int] = mapped_column(ForeignKey("themes.theme_id"))
    cluster_id: Mapped[int] = mapped_column(ForeignKey("clusters.cluster_id"))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

class Case(Base):
    __tablename__ = "cases"
    
    case_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    attributes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    case_assignments: Mapped[List["CaseAssignment"]] = relationship(back_populates="case")

class AISuggestion(Base):
    __tablename__ = "ai_suggestions"
    
    suggestion_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(255))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.source_id"))
    suggested_code_id: Mapped[Optional[int]] = mapped_column(ForeignKey("codes.code_id"))
    suggested_span: Mapped[Optional[str]] = mapped_column(Text)
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending") # pending, accepted, rejected, edited
    decision_reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

class JudgementNote(Base):
    __tablename__ = "judgement_notes"
    
    note_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    extract_id: Mapped[int] = mapped_column(ForeignKey("extracts.extract_id"))
    proposed_code_id: Mapped[Optional[int]] = mapped_column(ForeignKey("codes.code_id"))
    confidence: Mapped[Optional[str]] = mapped_column(String(50))
    trigger_phrases: Mapped[Optional[str]] = mapped_column(Text)
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    linked_rule: Mapped[Optional[str]] = mapped_column(Text)
    ladder_position: Mapped[Optional[str]] = mapped_column(String(255))
    alternatives_considered: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[Optional[str]] = mapped_column(String(100))
    user_id: Mapped[Optional[str]] = mapped_column(String(100))
    details: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

# --- New Models for v1.1 Academic Excellence ---

class TheoreticalFramework(Base):
    __tablename__ = "theoretical_frameworks"
    
    framework_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    
    dimensions: Mapped[List["FrameworkDimension"]] = relationship(back_populates="framework")

class FrameworkDimension(Base):
    __tablename__ = "framework_dimensions"
    
    dimension_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    framework_id: Mapped[int] = mapped_column(ForeignKey("theoretical_frameworks.framework_id"))
    name: Mapped[str] = mapped_column(String(255))
    definition: Mapped[str] = mapped_column(Text)
    mapped_code_id: Mapped[Optional[int]] = mapped_column(ForeignKey("codes.code_id"))
    
    framework: Mapped["TheoreticalFramework"] = relationship(back_populates="dimensions")
    mapped_code: Mapped[Optional["Code"]] = relationship(back_populates="framework_dimensions")

class CaseAssignment(Base):
    __tablename__ = "case_assignments"
    
    assignment_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.case_id"))
    source_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sources.source_id"))
    extract_id: Mapped[Optional[int]] = mapped_column(ForeignKey("extracts.extract_id"))
    assigned_by: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    
    case: Mapped["Case"] = relationship(back_populates="case_assignments")
    source: Mapped[Optional["Source"]] = relationship(back_populates="case_assignments")
    extract: Mapped[Optional["Extract"]] = relationship(back_populates="case_assignments")

class CodeIntersection(Base):
    __tablename__ = "code_intersections"
    
    intersection_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    extract_id: Mapped[int] = mapped_column(ForeignKey("extracts.extract_id"))
    code_a_id: Mapped[int] = mapped_column(ForeignKey("codes.code_id"))
    code_b_id: Mapped[int] = mapped_column(ForeignKey("codes.code_id"))
    relationship_type: Mapped[str] = mapped_column(String(50)) # tension, overlap, causal
    rationale: Mapped[str] = mapped_column(Text)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    
    extract: Mapped["Extract"] = relationship(back_populates="intersections")
    code_a: Mapped["Code"] = relationship(foreign_keys=[code_a_id])
    code_b: Mapped["Code"] = relationship(foreign_keys=[code_b_id])
