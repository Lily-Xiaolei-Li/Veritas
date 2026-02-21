/**
 * API Types
 *
 * B1.1 - Streaming Reasoning & Events
 */

// =============================================================================
// Health Check Types (B1.0)
// =============================================================================

export type HealthStatus = "healthy" | "degraded" | "unavailable";

export interface HealthCheck {
  status: HealthStatus;
  version: string;
  checks: {
    docker: string;
    database?: string;
  };
}

// =============================================================================
// Session Types (B1.1)
// =============================================================================

export interface Session {
  id: string;
  title: string;
  mode: string;
  status: string;
  config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  ended_at: string | null;
}

export interface SessionCreate {
  title: string;
  mode?: string;
}

export interface SessionUpdate {
  title?: string;
}

// =============================================================================
// Message Types (B1.1)
// =============================================================================

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface MessageCreate {
  content: string;
}

export interface MessageSubmitResponse {
  user_message: Message;
  run_id: string;
}

// =============================================================================
// SSE Event Types (B1.1)
// =============================================================================

/** Base interface for all SSE events */
interface SSEEventBase {
  run_id: string;
  seq: number;
}

/** Token event - streaming text content */
export interface TokenEvent extends SSEEventBase {
  content: string;
}

/** Tool invocation start event */
export interface ToolStartEvent extends SSEEventBase {
  tool_call_id: string;
  tool_name: string;
  input_preview: string;
}

/** Tool invocation end event */
export interface ToolEndEvent extends SSEEventBase {
  tool_call_id: string;
  exit_code: number;
  output_preview: string;
  duration_ms: number;
}

/** Error event */
export interface ErrorEvent extends SSEEventBase {
  message: string;
  recoverable: boolean;
}

/** Done event - stream completion (no additional fields beyond base) */
export type DoneEvent = SSEEventBase;

/** Union type for all SSE events */
export type SSEEvent =
  | { type: "token"; data: TokenEvent }
  | { type: "tool_start"; data: ToolStartEvent }
  | { type: "tool_end"; data: ToolEndEvent }
  | { type: "error"; data: ErrorEvent }
  | { type: "done"; data: DoneEvent };

// =============================================================================
// Tool Event Types (for UI state)
// =============================================================================

export type ToolEventStatus = "running" | "completed" | "failed";

export interface ToolEvent {
  tool_call_id: string;
  tool_name: string;
  input_preview: string;
  status: ToolEventStatus;
  output_preview?: string;
  exit_code?: number;
  duration_ms?: number;
  timestamp: number;
}

// =============================================================================
// Streaming Message Types (for UI state)
// =============================================================================

export interface StreamingMessage {
  run_id: string;
  content: string;
  isStreaming: boolean;
}

// =============================================================================
// File Types (B1.2)
// =============================================================================

/** Indexed file in the workspace */
export interface FileIndex {
  id: string;
  path: string;
  filename: string;
  extension: string | null;
  parent_dir: string;
  size_bytes: number;
  content_hash: string | null;
  mime_type: string | null;
  modified_at: string;
  indexed_at: string;
  is_deleted: boolean;
}

/** Paginated file list response */
export interface FileListResponse {
  files: FileIndex[];
  total: number;
  has_more: boolean;
  limit: number;
  offset: number;
}

/** File attachment to a session */
export interface FileAttachment {
  id: string;
  session_id: string;
  file_id: string;
  attached_at: string;
  file: FileIndex;
}

/** Response for attach files operation */
export interface AttachFilesResponse {
  attached: number;
  already_attached: number;
  not_found: number;
}

/** File list query parameters */
export interface FileListParams {
  limit?: number;
  offset?: number;
  sort?: "mtime_desc" | "name_asc" | "size_desc";
  prefix?: string;
  extension?: string;
  search?: string;
  include_deleted?: boolean;
}

// =============================================================================
// File SSE Event Types (B1.2)
// =============================================================================

/** File created event */
export interface FileCreatedEvent {
  file_id: string;
  path: string;
  filename: string;
  extension: string | null;
  size_bytes: number;
  modified_at: string;
}

/** File modified event */
export interface FileModifiedEvent {
  file_id: string;
  path: string;
  filename: string;
  extension: string | null;
  size_bytes: number;
  content_hash: string | null;
  modified_at: string;
}

/** File deleted event */
export interface FileDeletedEvent {
  file_id: string;
  path: string;
}

/** Extended SSE Event union including file events */
export type SSEEventExtended =
  | SSEEvent
  | { type: "file_created"; data: FileCreatedEvent }
  | { type: "file_modified"; data: FileModifiedEvent }
  | { type: "file_deleted"; data: FileDeletedEvent }
  | { type: "artifact_created"; data: ArtifactCreatedEvent }
  | { type: "artifact_deleted"; data: ArtifactDeletedEvent }
  | { type: "run_state_changed"; data: RunStateChangedEvent };

// =============================================================================
// Artifact Types (B1.3)
// =============================================================================

/** Preview kind for artifacts */
export type ArtifactPreviewKind = "text" | "code" | "markdown" | "image" | "none";

/** Artifact type classification */
export type ArtifactType = "file" | "stdout" | "stderr" | "log";

/** Artifact produced by agent runs */
export interface Artifact {
  id: string;
  run_id: string;
  session_id: string;
  display_name: string;
  storage_path: string;
  extension: string | null;
  size_bytes: number;
  content_hash: string | null;
  mime_type: string | null;
  artifact_type: ArtifactType;
  created_at: string;
  artifact_meta: Record<string, unknown> | null;
  is_deleted: boolean;
  // Computed fields from server
  can_preview: boolean;
  preview_kind: ArtifactPreviewKind;
  download_url: string;
}

/** Paginated artifact list response */
export interface ArtifactListResponse {
  artifacts: Artifact[];
  total: number;
  has_more: boolean;
  limit: number;
  offset: number;
}

/** Artifact preview response */
export interface ArtifactPreview {
  kind: ArtifactPreviewKind;
  content_type: string;
  truncated: boolean;
  text: string | null;
}

/** Artifact list query parameters */
export interface ArtifactListParams {
  limit?: number;
  offset?: number;
  sort?: "created_desc" | "name_asc" | "size_desc";
  artifact_type?: ArtifactType;
  extension?: string;
  include_deleted?: boolean;
}

// =============================================================================
// Artifact SSE Event Types (B1.3)
// =============================================================================

/** Artifact created event (broadcast when an artifact is created) */
export interface ArtifactCreatedEvent {
  artifact: Artifact;
}

/** Artifact deleted event (soft delete) */
export interface ArtifactDeletedEvent {
  artifact_id: string;
  session_id: string;
  run_id: string;
}

/** Run state changed event */
export interface RunStateChangedEvent {
  run_id: string;
  session_id: string;
  status: string;
  error?: string | null;
}

// =============================================================================
// Kill Switch Types (B1.4)
// =============================================================================

/** Termination reason */
export type TerminationReason = "user_cancel" | "timeout" | "error" | "system";

/** Cancel status */
export type CancelStatus =
  | "task_cancelled"
  | "container_stopped"
  | "container_killed"
  | "already_stopped"
  | "none";

/** Run terminated event (kill switch) */
export interface RunTerminatedEvent {
  run_id: string;
  session_id: string;
  terminated_at: string;
  reason: TerminationReason;
  cancel_status: CancelStatus;
  latency_ms: number;
  message?: string;
}

/** Terminate response from API */
export interface TerminateResponse {
  status: "terminated" | "no_active_run" | "failed";
  run_id?: string;
  reason: string;
  cancel_status: string;
  latency_ms: number;
  message?: string;
}

// =============================================================================
// Authentication Types (B1.6)
// =============================================================================

/** Login request payload */
export interface LoginRequest {
  username: string;
  password: string;
}

/** Login response from backend */
export interface LoginResponse {
  token: string;
  user_id: string;
  username: string;
  expires_in_hours: number;
}

/** User info (reconstructed from token/login response) */
export interface AuthUser {
  user_id: string;
  username: string;
}

/** Auth status tri-state + offline */
export type AuthStatus = "checking" | "offline" | "disabled" | "enabled";

// =============================================================================
// API Key Types (B1.6)
// =============================================================================

/** API key stored in backend (key value never returned) */
export interface ApiKey {
  id: string;
  name: string;
  provider: string;
  created_at: string;
  last_used_at: string | null;
  is_active: boolean;
}

/** Request to create a new API key */
export interface ApiKeyCreate {
  name: string;
  provider: string;
  key: string;
}

/** Query parameters for listing API keys */
export interface ApiKeyListParams {
  provider?: string;
  active_only?: boolean;
}

// =============================================================================
// Run Types (B2.1)
// =============================================================================

/** Run status values (B2.1 canonical) */
export type RunStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "terminated"
  | "interrupted";

/** Execution status for UI state */
export type ExecutionStatus =
  | "idle"
  | "running"
  | "terminating"
  | "completed"
  | "failed"
  | "terminated"
  | "interrupted";

/** Statuses that allow resume */
export const RESUMABLE_STATUSES: RunStatus[] = ["terminated", "failed", "interrupted"];

/** Run record from backend */
export interface Run {
  id: string;
  session_id: string;
  task: string;
  status: RunStatus;
  result: string | null;
  error: string | null;
  escalated: boolean;
  escalation_reason: string | null;
  brain_used: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  has_checkpoints: boolean;
}

/** Paginated run list response */
export interface RunListResponse {
  runs: Run[];
  total: number;
  limit: number;
  offset: number;
}

/** Resume run response */
export interface ResumeResponse {
  run_id: string;
  status: string;
  message: string;
}

/** Run list query parameters */
export interface RunListParams {
  limit?: number;
  offset?: number;
}

// =============================================================================
// Extended SSE Events (B2.1)
// =============================================================================

/** Checkpoint created event */
export interface CheckpointCreatedEvent {
  run_id: string;
  seq: number;
  checkpoint_id: string;
  node: string;
}

/** Run resumed event */
export interface RunResumedEvent {
  run_id: string;
  seq: number;
  from_checkpoint: string;
}

/** Extended SSE Event union including B2.1 events */
export type SSEEventB21 =
  | SSEEventExtended
  | { type: "checkpoint_created"; data: CheckpointCreatedEvent }
  | { type: "run_resumed"; data: RunResumedEvent }
  | { type: "run_terminated"; data: { run_id: string; seq: number; reason: string } };

// =============================================================================
// Multi-Brain Event Types (B2.2)
// =============================================================================

/** Classification reason codes */
export type ClassificationReasonCode =
  | "ONE_STEP_QA"
  | "MULTI_STEP_PLAN"
  | "TOOL_REQUIRED"
  | "AMBIGUOUS";

/** Task complexity levels */
export type TaskComplexity = "simple" | "complex";

/** Collaboration modes */
export type CollaborationMode = "solo" | "consensus";

/** Classification event - when Brain 1 classifies a task */
export interface ClassificationEvent {
  run_id: string;
  seq: number;
  complexity: TaskComplexity;
  mode: CollaborationMode;
  reason_code: ClassificationReasonCode;
  rationale: string;
  brain_provider?: string;
  brain_model?: string;
}

/** Brain decision structure */
export interface BrainDecisionData {
  decision: "answer" | "use_tool" | "ask_user" | "escalate";
  intent: "answer_only" | "plan_only" | "run_bash" | "ask_user" | "escalate";
  tool_name: string | null;
  target_artifacts: string[];
  plan_steps: string[];
  key_risks: string[];
  summary: string;
}

/** Brain thinking event - when a brain provides its reasoning */
export interface BrainThinkingEvent {
  run_id: string;
  seq: number;
  brain: "B1" | "B2";
  decision: BrainDecisionData;
  full_reasoning: string;
  brain_provider?: string;
  brain_model?: string;
}

/** Deliberation round event - shows both brain positions */
export interface DeliberationRoundEvent {
  run_id: string;
  seq: number;
  round_display: number;
  max_rounds: number;
  b1_decision: BrainDecisionData;
  b2_decision: BrainDecisionData;
}

/** Consensus reached event */
export interface ConsensusReachedEvent {
  run_id: string;
  seq: number;
  intent: string;
  tool_name: string | null;
  target_artifacts: string[];
}

/** Consensus failed event */
export interface ConsensusFailedEvent {
  run_id: string;
  seq: number;
  rounds: number;
  reason: string;
}

/** Escalation required event - distinct from normal completion */
export interface EscalationRequiredEvent {
  run_id: string;
  seq: number;
  objective: string;
  rounds_attempted: number;
  b1_summary: string;
  b2_summary: string;
  reason: "MAX_ROUNDS" | "BRAIN_REQUESTED";
}

/** State truncation event (for observability) */
export interface StateTruncatedEvent {
  run_id: string;
  seq: number;
  field_name: string;
  original_length: number;
  capped_length: number;
}

/** Union type for all B2.2 multi-brain events */
export type MultiBrainEvent =
  | { type: "classification"; data: ClassificationEvent }
  | { type: "brain_thinking"; data: BrainThinkingEvent }
  | { type: "deliberation_round"; data: DeliberationRoundEvent }
  | { type: "consensus_reached"; data: ConsensusReachedEvent }
  | { type: "consensus_failed"; data: ConsensusFailedEvent }
  | { type: "escalation_required"; data: EscalationRequiredEvent }
  | { type: "state_truncated"; data: StateTruncatedEvent };

/** Brain event for UI state (stored in workbench store) */
export interface BrainEvent {
  id: string;
  run_id: string;
  type: MultiBrainEvent["type"];
  data: MultiBrainEvent["data"];
  timestamp: number;
}

/** Extended SSE Event union including B2.2 events */
export type SSEEventB22 =
  | SSEEventB21
  | MultiBrainEvent;
