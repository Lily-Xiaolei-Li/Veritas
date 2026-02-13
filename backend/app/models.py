"""
Database models for Agent B.

Initial schema (B0.0.2):
- sessions: User interaction sessions
- runs: Individual agent runs within a session
- events: Events that occur during runs
- audit_log: System-wide audit trail

B0.0.4 additions:
- users: User credentials for authentication
- api_keys: Encrypted API keys for LLM providers
- state_snapshots: LangGraph state persistence

B0.3 additions:
- messages: Chat messages within sessions

B1.2 additions:
- file_index: Workspace file metadata for browsing
- session_file_attachments: Files attached to sessions

B1.3 additions:
- artifacts: Agent-generated output files

B2.0 additions:
- llm_usage: LLM API usage tracking for cost and observability

B3.0 additions:
- personas: Customizable system prompts (Phase 6)
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Integer,
    BigInteger,
    Boolean,
    JSON,
    ForeignKey,
    func,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Session(Base):
    """
    User interaction session.

    A session represents a continuous period of interaction with Agent B.
    Sessions can contain multiple runs.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Session metadata
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mode: Mapped[str] = mapped_column(
        String(50), nullable=False, default="engineering"
    )  # e.g., engineering, creative, conservative
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )  # active, paused, completed, error

    # Configuration snapshot
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Workspace persistence (Phase 1)
    workspace_state: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    workspace_state_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    last_auto_save_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Indexes for common queries
    __table_args__ = (
        Index("ix_sessions_created_at", "created_at"),
        Index("ix_sessions_status", "status"),
    )


class Run(Base):
    """
    Individual agent run within a session.

    A run represents a single task execution by Agent B.
    Each run belongs to a session.
    """

    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )  # Foreign key to sessions

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Run details
    task: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending"
    )  # pending, running, completed, failed, escalated
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Escalation tracking
    escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    escalation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Brain tracking (for multi-brain architecture)
    brain_used: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # brain_1, brain_2, brain_3

    # Run metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    run_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Indexes
    __table_args__ = (
        Index("ix_runs_session_id", "session_id"),
        Index("ix_runs_created_at", "created_at"),
        Index("ix_runs_status", "status"),
        Index("ix_runs_escalated", "escalated"),
    )


class RagSource(Base):
    """Managed RAG source (corpus) metadata."""

    __tablename__ = "rag_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # preset: papers | interviews | books | generic
    preset: Mapped[str] = mapped_column(String(50), nullable=False, default="generic")

    # status: creating | ready | indexing | failed | deleted
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="creating", index=True)

    source_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_rag_sources_name", "name"),
        Index("ix_rag_sources_status", "status"),
    )


class Event(Base):
    """
    Events that occur during runs.

    Events capture all significant actions, decisions, and state changes
    during agent execution. This provides detailed observability.
    """

    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )  # Foreign key to runs
    session_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )  # Denormalized for easier querying

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Event classification
    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # tool_call, llm_request, escalation, decision, error, etc.
    component: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Which component generated this event

    # Event data
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True
    )  # Structured event data

    # Severity for filtering
    severity: Mapped[str] = mapped_column(
        String(20), nullable=False, default="info"
    )  # debug, info, warning, error, critical

    # Future-proofing for Phase 3 consultation circles (B0.0.4)
    circle_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )  # Consultation circle identifier
    rationale: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Rationale for decision/action

    # Indexes
    __table_args__ = (
        Index("ix_events_run_id", "run_id"),
        Index("ix_events_session_id", "session_id"),
        Index("ix_events_created_at", "created_at"),
        Index("ix_events_event_type", "event_type"),
        Index("ix_events_severity", "severity"),
        Index("ix_events_circle_id", "circle_id"),
    )


class AuditLog(Base):
    """
    System-wide audit trail.

    Captures security-relevant events, configuration changes,
    and other system-level actions that need to be tracked.
    """

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Who/what performed the action
    actor: Mapped[str] = mapped_column(String(100), nullable=False)  # user, system, agent
    actor_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Identifier for the actor

    # What action was performed
    action: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # login, config_change, key_rotation, etc.
    resource: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # What was acted upon

    # Context
    session_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Details
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Outcome
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Future-proofing for Phase 3 consultation circles (B0.0.4)
    circle_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, index=True
    )  # Consultation circle identifier
    rationale: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Rationale for decision/action

    # Indexes
    __table_args__ = (
        Index("ix_audit_log_created_at", "created_at"),
        Index("ix_audit_log_action", "action"),
        Index("ix_audit_log_actor", "actor"),
        Index("ix_audit_log_session_id", "session_id"),
        Index("ix_audit_log_circle_id", "circle_id"),
    )


class User(Base):
    """
    User accounts for authentication (B0.0.4).

    Stores user credentials for optional password protection.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    username: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Indexes
    __table_args__ = (
        Index("ix_users_username", "username", unique=True),
        Index("ix_users_is_active", "is_active"),
    )


class LLMProviderConfig(Base):
    """Provider configuration stored in DB (Phase 2).

    This replaces the over-engineered encrypted API key store for local/dev use.
    Stores provider config as JSON (including API keys) for simplicity.

    NOTE: No encryption at rest in this Phase 2 implementation.
    """

    __tablename__ = "llm_provider_configs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    provider: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)

    # Provider config JSON blob. Expected to contain fields like baseUrl, apiKey, models, etc.
    config_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_llm_provider_configs_provider", "provider", unique=True),
        Index("ix_llm_provider_configs_updated_at", "updated_at"),
    )


class APIKey(Base):
    """
    Encrypted storage for API keys (B0.0.4).

    Stores LLM provider API keys encrypted at rest.
    """

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # gemini, openrouter, openai, anthropic, etc.

    # Encrypted API key
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Indexes
    __table_args__ = (
        Index("ix_api_keys_provider", "provider"),
        Index("ix_api_keys_is_active", "is_active"),
        Index("ix_api_keys_created_at", "created_at"),
    )


class StateSnapshot(Base):
    """
    LangGraph state persistence (B0.0.4 future-proofing for B2.1).

    Stores checkpoints of LangGraph execution state to enable
    resumption after restarts.
    """

    __tablename__ = "state_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    checkpoint_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # Serialized state data
    state_data: Mapped[dict] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Indexes
    __table_args__ = (
        Index("ix_state_snapshots_run_id", "run_id"),
        Index("ix_state_snapshots_checkpoint_id", "checkpoint_id"),
        Index("ix_state_snapshots_created_at", "created_at"),
    )


class Message(Base):
    """
    Chat messages within sessions (B0.3).

    Stores user and assistant messages in a conversation.
    """

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )  # Foreign key to sessions

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Message details
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Indexes
    __table_args__ = (
        Index("ix_messages_session_id", "session_id"),
        Index("ix_messages_created_at", "created_at"),
    )


class FileIndex(Base):
    """
    File index for workspace browsing (B1.2).

    Stores metadata about files in the workspace directory for fast browsing
    and change detection. Files are indexed by a background watcher.
    """

    __tablename__ = "file_index"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # File path (relative to workspace_dir)
    path: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    extension: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # e.g., "py", "txt" (no dot)
    parent_dir: Mapped[str] = mapped_column(
        String(1024), nullable=False
    )  # Parent directory path for prefix queries

    # File metadata
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )  # SHA-256 (nullable for large files)
    hash_algo: Mapped[str] = mapped_column(
        String(16), nullable=False, default="sha256"
    )
    mime_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Optional, computed on demand

    # Timestamps
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )  # File's mtime
    indexed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Soft delete for audit trail
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Indexes for fast browsing
    __table_args__ = (
        Index("ix_file_index_path", "path", unique=True),
        Index("ix_file_index_parent_dir", "parent_dir"),
        Index("ix_file_index_extension", "extension"),
        Index("ix_file_index_is_deleted", "is_deleted"),
        Index("ix_file_index_modified_at", "modified_at"),
        Index("ix_file_index_content_hash", "content_hash"),
    )


class SessionFileAttachment(Base):
    """
    Files attached to sessions (B1.2).

    Join table linking sessions to files from the file index.
    """

    __tablename__ = "session_file_attachments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )  # Foreign key to sessions
    file_id: Mapped[str] = mapped_column(
        String(36), nullable=False
    )  # Foreign key to file_index

    attached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Indexes
    __table_args__ = (
        Index("ix_session_file_attachments_session_id", "session_id"),
        Index("ix_session_file_attachments_file_id", "file_id"),
        Index(
            "ix_session_file_attachments_unique",
            "session_id",
            "file_id",
            unique=True,
        ),
    )


class Artifact(Base):
    """
    Artifact produced by agent runs (B1.3).

    Stores metadata about files generated during agent execution.
    Actual content stored in filesystem at:
    {artifacts_dir}/{session_id}/{run_id}/{artifact_id}_{filename}
    """

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Foreign keys with proper constraints
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # File identification
    display_name: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Original user-facing filename
    storage_path: Mapped[str] = mapped_column(
        String(1024), nullable=False
    )  # Deterministic path: {session_id}/{run_id}/{artifact_id}_{filename}
    extension: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # e.g., "py", "txt" (no dot)

    # Content metadata
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )  # SHA-256
    mime_type: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g., "text/plain", "image/png"

    # Classification
    artifact_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="file"
    )  # file, stdout, stderr, log

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Flexible metadata (named artifact_meta to avoid SQLAlchemy reserved name)
    artifact_meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Draft support (Phase 1)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="upload"
    )  # upload, tool, chat, editor, import
    is_draft: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    draft_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    draft_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Soft delete for audit trail
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Composite indexes for fast queries
    __table_args__ = (
        Index("ix_artifacts_session_created", "session_id", "created_at"),
        Index("ix_artifacts_run_created", "run_id", "created_at"),
        Index("ix_artifacts_artifact_type", "artifact_type"),
        Index("ix_artifacts_extension", "extension"),
        Index("ix_artifacts_is_deleted", "is_deleted"),
    )


class Persona(Base):
    """Persona definition (Phase 6).

    Stores named system prompts to shape assistant behaviour.
    """

    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # Display order for dropdown + UI
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        Index("ix_personas_is_deleted", "is_deleted"),
        Index("ix_personas_label", "label"),
        Index("ix_personas_sort_order", "sort_order"),
    )


class LLMUsage(Base):
    """
    LLM API usage tracking (B2.0).

    Records every LLM API call for cost tracking and observability.
    Token and cost fields are nullable because not all providers
    return this data for every request.
    """

    __tablename__ = "llm_usage"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Context (optional - not all requests have these)
    run_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)

    # Provider/Model identification
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    request_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="complete"
    )  # complete, stream

    # Request status
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )  # success, error
    error_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # ErrorType value or null

    # Token usage (nullable - not always available)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_unavailable_reason: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g., "streaming", "provider_unsupported"

    # Cost (stored as integer cents for precision, nullable)
    input_cost_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_cost_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_cost_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_unavailable_reason: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g., "pricing_unknown", "tokens_unavailable"

    # Performance (always available)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    total_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # Provider metadata
    provider_request_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    finish_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    attempted_providers: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array of provider names tried

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_llm_usage_session_created", "session_id", "created_at"),
        Index("ix_llm_usage_provider_created", "provider", "created_at"),
        Index("ix_llm_usage_status", "status"),
        Index("ix_llm_usage_model", "model"),
    )
