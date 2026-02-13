/**
 * Workbench Store (B1.4 - Kill Switch)
 *
 * Zustand store for managing:
 * - Current session state
 * - Message history
 * - Streaming message state
 * - Tool events from SSE
 * - Connection status
 * - File selection state (B1.2)
 * - Artifact selection state (B1.3)
 * - Execution state (B1.4)
 *
 * B1.6: Auth state moved to separate authStore.ts
 */

import { create } from "zustand";
import type { LocalArtifact } from "@/lib/artifacts/types";

// Re-export auth store for convenience
export { useAuthStore, selectToken, selectAuthStatus, selectUser, selectIsAuthenticated, selectSessionExpiredShown } from "./authStore";

// =============================================================================
// Types
// =============================================================================

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface ToolEvent {
  tool_call_id: string;
  tool_name: string;
  input_preview: string;
  status: "running" | "completed" | "failed";
  output_preview?: string;
  exit_code?: number;
  duration_ms?: number;
  timestamp: number;
}

// B2.2 Multi-Brain Events
export interface BrainEvent {
  id: string;
  run_id: string;
  type: "classification" | "brain_thinking" | "deliberation_round" | "consensus_reached" | "consensus_failed" | "escalation_required";
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any; // Use any for flexibility with different event types
  timestamp: number;
}

export interface StreamingMessage {
  run_id: string;
  content: string;
  isStreaming: boolean;
}

// Outbound payload preview for Events panel (Phase 2)
export interface OutboundPreviewChunk {
  label: string;
  preview: string;
}

export interface OutboundPreview {
  persona_id: string;
  user_message: string;
  context_chunks: OutboundPreviewChunk[];
  updated_at: number;
}

// Execution state for kill switch (B1.4)
export type ExecutionStatus =
  | "idle"
  | "running"
  | "terminating"
  | "terminated"
  | "completed"
  | "failed";

export interface TerminationInfo {
  reason: string;
  message?: string;
  latency_ms?: number;
}

// Text selection for contextual editing
export interface TextSelection {
  id: string;
  artifactId: string;
  artifactName: string;
  startLine: number;
  endLine: number;
  text: string;
  timestamp: number;
}

// =============================================================================
// Store Interface
// =============================================================================

interface WorkbenchState {
  // Session state
  currentSessionId: string | null;

  // Message state
  messages: Message[];
  streamingMessage: StreamingMessage | null;

  // Tool events
  toolEvents: ToolEvent[];

  // Brain events (B2.2 - Multi-brain transparency)
  brainEvents: BrainEvent[];

  // SSE connection state
  sseConnected: boolean;
  sseError: string | null;

  // File selection state (B1.2) - use string[] for serialization
  selectedFileIds: string[];

  // Artifact selection state (B1.3)
  selectedArtifactId: string | null; // currently opened in preview
  focusedArtifactIds: string[]; // pinned / high-priority context
  checkedArtifactIds: string[]; // checkbox-selected for batch operations
  focusMode: "prefer" | "only";
  artifactScope: "session" | "all_sessions";
  externalSources: Record<string, string>; // placeholder for future RAG libraries

  // Edit target state (B1.7 - Edit Toggle)
  editTargetArtifactId: string | null; // artifact to be updated by AI output
  editTargetSelections: TextSelection[]; // specific sections to edit within the artifact

  // UI preferences
  theme: "light" | "dark";

  localArtifacts: LocalArtifact[];
  artifactEdits: Record<string, string>;

  // Execution state (B1.4 - Kill Switch)
  activeRunId: string | null;
  executionStatus: ExecutionStatus;
  terminationInfo: TerminationInfo | null;

  // Text selections for contextual editing
  textSelections: TextSelection[];

  // Selected persona for AI behavior
  selectedPersonaId: string;

  // Phase 2: Events panel preview of what will be sent
  outboundPreview: OutboundPreview | null;

  // Conversation refresh token (increment to force ConversationTab refetch)
  conversationRefreshToken: number;

  // Session actions
  setCurrentSession: (sessionId: string | null) => void;

  // Message actions
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  appendToStreamingMessage: (runId: string, content: string) => void;
  finalizeStreamingMessage: (runId: string) => void;
  clearMessages: () => void;

  // Tool event actions
  addToolEvent: (event: Omit<ToolEvent, "timestamp">) => void;
  updateToolEvent: (toolCallId: string, updates: Partial<ToolEvent>) => void;
  clearToolEvents: () => void;
  markRunningToolsAsFailed: (message: string) => void;

  // Brain event actions (B2.2)
  addBrainEvent: (event: Omit<BrainEvent, "id" | "timestamp">) => void;
  clearBrainEvents: () => void;

  // SSE connection actions
  setSSEConnected: (connected: boolean) => void;
  setSSEError: (error: string | null) => void;

  // File selection actions (B1.2)
  toggleFileSelection: (fileId: string) => void;
  selectAllFiles: (fileIds: string[]) => void;
  clearFileSelection: () => void;
  isFileSelected: (fileId: string) => boolean;

  // Artifact selection actions (B1.3)
  setSelectedArtifact: (artifactId: string | null) => void;
  toggleFocusedArtifact: (artifactId: string) => void;
  clearFocusedArtifacts: () => void;
  setFocusMode: (mode: "prefer" | "only") => void;
  setArtifactScope: (scope: "session" | "all_sessions") => void;
  setExternalSourceMode: (sourceKey: string, mode: string) => void;

  // Edit target actions (B1.7 - Edit Toggle)
  setEditTarget: (artifactId: string | null) => void;
  toggleEditTarget: (artifactId: string) => void;
  addEditTargetSelection: (selection: Omit<TextSelection, "id" | "timestamp">) => void;
  removeEditTargetSelection: (selectionId: string) => void;
  clearEditTargetSelections: () => void;
  toggleEditTargetSelection: (selection: Omit<TextSelection, "id" | "timestamp">) => void;

  // Batch selection actions
  toggleCheckedArtifact: (artifactId: string) => void;
  setCheckedArtifacts: (artifactIds: string[]) => void;
  clearCheckedArtifacts: () => void;
  focusCheckedArtifacts: () => void;

  setTheme: (theme: "light" | "dark") => void;

  addLocalArtifact: (artifact: LocalArtifact) => void;
  removeLocalArtifact: (artifactId: string) => void;
  updateArtifactEdit: (artifactId: string, content: string) => void;
  removeArtifactEdit: (artifactId: string) => void;
  clearLocalArtifacts: () => void;
  clearArtifactEdits: () => void;

  // Execution state actions (B1.4 - Kill Switch)
  setActiveRun: (runId: string) => void;
  setTerminating: () => void;
  markTerminated: (info: TerminationInfo) => void;
  markCompleted: () => void;
  markFailed: (error: string) => void;
  clearExecutionState: () => void;

  // Text selection actions
  addTextSelection: (selection: Omit<TextSelection, "id" | "timestamp">) => void;
  removeTextSelection: (selectionId: string) => void;
  clearTextSelections: () => void;
  toggleTextSelection: (selection: Omit<TextSelection, "id" | "timestamp">) => void;

  // Persona actions
  setSelectedPersona: (personaId: string) => void;

  // Phase 2: Outbound preview actions
  setOutboundPreview: (preview: Omit<OutboundPreview, "updated_at">) => void;
  clearOutboundPreview: () => void;

  // Conversation refresh actions
  bumpConversationRefresh: () => void;

  // Editor maximize state
  isEditorMaximized: boolean;
  toggleEditorMaximized: () => void;
}

// =============================================================================
// Store Implementation
// =============================================================================

export const useWorkbenchStore = create<WorkbenchState>((set, get) => ({
  // Initial state
  currentSessionId: null,
  messages: [],
  streamingMessage: null,
  toolEvents: [],
  brainEvents: [],
  sseConnected: false,
  sseError: null,
  selectedFileIds: [],
  selectedArtifactId: null,
  focusedArtifactIds: [],
  checkedArtifactIds: [],
  focusMode: "prefer",
  artifactScope: "session",
  externalSources: {},
  // Edit target state (B1.7)
  editTargetArtifactId: null,
  editTargetSelections: [],
  theme: "dark",
  localArtifacts: [],
  artifactEdits: {},
  // Execution state (B1.4)
  activeRunId: null,
  executionStatus: "idle",
  terminationInfo: null,

  // Text selections
  textSelections: [],

  // Persona
  selectedPersonaId: "default",

  // Phase 2: outbound preview
  outboundPreview: null,

  conversationRefreshToken: 0,

  // Editor maximize state
  isEditorMaximized: false,

  // Session actions
  setCurrentSession: (sessionId) =>
    set({
      currentSessionId: sessionId,
      // Clear state when session changes
      messages: [],
      streamingMessage: null,
      toolEvents: [],
      brainEvents: [],
      sseError: null,
      localArtifacts: [],
      artifactEdits: {},
      focusedArtifactIds: [],
      // Clear edit target when switching sessions
      editTargetArtifactId: null,
      editTargetSelections: [],
      // Keep theme preference across sessions
      theme: get().theme,
      // Reset execution state
      activeRunId: null,
      executionStatus: "idle",
      terminationInfo: null,

      // Reset outbound preview
      outboundPreview: null,

      conversationRefreshToken: 0,
    }),

  // Message actions
  setMessages: (messages) => set({ messages }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  appendToStreamingMessage: (runId, content) =>
    set((state) => {
      // If different run, start fresh (handles reconnection edge case)
      if (state.streamingMessage?.run_id !== runId) {
        return {
          streamingMessage: {
            run_id: runId,
            content,
            isStreaming: true,
          },
        };
      }

      // Append to existing
      return {
        streamingMessage: {
          ...state.streamingMessage,
          content: state.streamingMessage.content + content,
        },
      };
    }),

  finalizeStreamingMessage: (runId) =>
    set((state) => {
      // Only finalize if it's the matching run
      if (state.streamingMessage?.run_id !== runId) {
        return {};
      }

      // Move streaming content to a new assistant message
      const assistantMessage: Message = {
        id: `streaming-${runId}`,
        session_id: state.currentSessionId || "",
        role: "assistant",
        content: state.streamingMessage.content,
        created_at: new Date().toISOString(),
      };

      return {
        messages: [...state.messages, assistantMessage],
        streamingMessage: null,
      };
    }),

  clearMessages: () => set({ messages: [], streamingMessage: null }),

  // Tool event actions
  addToolEvent: (event) =>
    set((state) => ({
      toolEvents: [
        ...state.toolEvents,
        {
          ...event,
          timestamp: Date.now(),
        },
      ],
    })),

  updateToolEvent: (toolCallId, updates) =>
    set((state) => ({
      toolEvents: state.toolEvents.map((e) =>
        e.tool_call_id === toolCallId ? { ...e, ...updates } : e
      ),
    })),

  clearToolEvents: () => set({ toolEvents: [] }),

  // Brain event actions (B2.2)
  addBrainEvent: (event) =>
    set((state) => ({
      brainEvents: [
        ...state.brainEvents,
        {
          ...event,
          id: `brain-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
          timestamp: Date.now(),
        },
      ],
    })),

  clearBrainEvents: () => set({ brainEvents: [] }),

  markRunningToolsAsFailed: (message) =>
    set((state) => ({
      toolEvents: state.toolEvents.map((e) =>
        e.status === "running"
          ? { ...e, status: "failed" as const, output_preview: message }
          : e
      ),
    })),

  // SSE connection actions
  setSSEConnected: (connected) =>
    set({
      sseConnected: connected,
      // Clear error on successful connection
      sseError: connected ? null : get().sseError,
    }),

  setSSEError: (error) => set({ sseError: error }),

  // File selection actions (B1.2)
  toggleFileSelection: (fileId) =>
    set((state) => {
      const isSelected = state.selectedFileIds.includes(fileId);
      if (isSelected) {
        return {
          selectedFileIds: state.selectedFileIds.filter((id) => id !== fileId),
        };
      }
      return {
        selectedFileIds: [...state.selectedFileIds, fileId],
      };
    }),

  selectAllFiles: (fileIds) => set({ selectedFileIds: fileIds }),

  clearFileSelection: () => set({ selectedFileIds: [] }),

  isFileSelected: (fileId) => get().selectedFileIds.includes(fileId),

  // Artifact selection actions (B1.3)
  setSelectedArtifact: (artifactId) => set({ selectedArtifactId: artifactId }),

  toggleFocusedArtifact: (artifactId) =>
    set((state) => {
      const exists = state.focusedArtifactIds.includes(artifactId);
      return {
        focusedArtifactIds: exists
          ? state.focusedArtifactIds.filter((id) => id !== artifactId)
          : [...state.focusedArtifactIds, artifactId],
      };
    }),

  clearFocusedArtifacts: () => set({ focusedArtifactIds: [] }),

  setFocusMode: (mode) => set({ focusMode: mode }),

  setArtifactScope: (scope) => set({ artifactScope: scope }),

  setExternalSourceMode: (sourceKey, mode) =>
    set((state) => ({
      externalSources: { ...state.externalSources, [sourceKey]: mode },
    })),

  // Edit target actions (B1.7 - Edit Toggle)
  setEditTarget: (artifactId) =>
    set({
      editTargetArtifactId: artifactId,
      editTargetSelections: [], // Clear selections when changing target
    }),

  toggleEditTarget: (artifactId) =>
    set((state) => ({
      editTargetArtifactId: state.editTargetArtifactId === artifactId ? null : artifactId,
      editTargetSelections: state.editTargetArtifactId === artifactId ? [] : state.editTargetSelections,
    })),

  addEditTargetSelection: (selection) =>
    set((state) => ({
      editTargetSelections: [
        ...state.editTargetSelections,
        {
          ...selection,
          id: `edit-sel-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          timestamp: Date.now(),
        },
      ],
    })),

  removeEditTargetSelection: (selectionId) =>
    set((state) => ({
      editTargetSelections: state.editTargetSelections.filter((s) => s.id !== selectionId),
    })),

  clearEditTargetSelections: () => set({ editTargetSelections: [] }),

  toggleEditTargetSelection: (selection) =>
    set((state) => {
      const existing = state.editTargetSelections.find(
        (s) =>
          s.artifactId === selection.artifactId &&
          s.startLine === selection.startLine &&
          s.endLine === selection.endLine
      );

      if (existing) {
        return {
          editTargetSelections: state.editTargetSelections.filter((s) => s.id !== existing.id),
        };
      }

      return {
        editTargetSelections: [
          ...state.editTargetSelections,
          {
            ...selection,
            id: `edit-sel-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            timestamp: Date.now(),
          },
        ],
      };
    }),

  // Batch selection actions
  toggleCheckedArtifact: (artifactId) =>
    set((state) => {
      const exists = state.checkedArtifactIds.includes(artifactId);
      return {
        checkedArtifactIds: exists
          ? state.checkedArtifactIds.filter((id) => id !== artifactId)
          : [...state.checkedArtifactIds, artifactId],
      };
    }),

  setCheckedArtifacts: (artifactIds) => set({ checkedArtifactIds: artifactIds }),

  clearCheckedArtifacts: () => set({ checkedArtifactIds: [] }),

  focusCheckedArtifacts: () =>
    set((state) => {
      // Add all checked artifacts to focused (without duplicates)
      const newFocused = [...new Set([...state.focusedArtifactIds, ...state.checkedArtifactIds])];
      return {
        focusedArtifactIds: newFocused,
        checkedArtifactIds: [], // Clear checked after focusing
      };
    }),

  setTheme: (theme) => set({ theme }),
  addLocalArtifact: (artifact) =>
    set((state) => ({
      localArtifacts: [artifact, ...state.localArtifacts],
      artifactEdits: {
        ...state.artifactEdits,
        [artifact.id]: artifact.content,
      },
    })),
  removeLocalArtifact: (artifactId) =>
    set((state) => ({
      localArtifacts: state.localArtifacts.filter((a) => a.id !== artifactId),
    })),
  updateArtifactEdit: (artifactId, content) =>
    set((state) => ({
      artifactEdits: {
        ...state.artifactEdits,
        [artifactId]: content,
      },
    })),
  removeArtifactEdit: (artifactId) =>
    set((state) => {
      const next = { ...state.artifactEdits };
      delete next[artifactId];
      return { artifactEdits: next };
    }),
  clearLocalArtifacts: () => set({ localArtifacts: [] }),
  clearArtifactEdits: () => set({ artifactEdits: {} }),

  // Execution state actions (B1.4 - Kill Switch)
  setActiveRun: (runId) =>
    set({
      activeRunId: runId,
      executionStatus: "running",
      terminationInfo: null,
    }),

  setTerminating: () =>
    set((state) => ({
      executionStatus: state.executionStatus === "running" ? "terminating" : state.executionStatus,
    })),

  markTerminated: (info) =>
    set((state) => {
      // Mark running tools as failed
      const updatedToolEvents = state.toolEvents.map((e) =>
        e.status === "running"
          ? { ...e, status: "failed" as const, output_preview: `Terminated: ${info.reason}` }
          : e
      );

      return {
        executionStatus: "terminated",
        terminationInfo: info,
        toolEvents: updatedToolEvents,
        streamingMessage: null,
      };
    }),

  markCompleted: () =>
    set({
      executionStatus: "completed",
      activeRunId: null,
    }),

  markFailed: (error) =>
    set({
      executionStatus: "failed",
      sseError: error,
    }),

  clearExecutionState: () =>
    set({
      activeRunId: null,
      executionStatus: "idle",
      terminationInfo: null,
    }),

  // Text selection actions
  addTextSelection: (selection) =>
    set((state) => ({
      textSelections: [
        ...state.textSelections,
        {
          ...selection,
          id: `sel-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          timestamp: Date.now(),
        },
      ],
    })),

  removeTextSelection: (selectionId) =>
    set((state) => ({
      textSelections: state.textSelections.filter((s) => s.id !== selectionId),
    })),

  clearTextSelections: () => set({ textSelections: [] }),

  toggleTextSelection: (selection) =>
    set((state) => {
      // Check if a selection with same artifact and line range exists
      const existing = state.textSelections.find(
        (s) =>
          s.artifactId === selection.artifactId &&
          s.startLine === selection.startLine &&
          s.endLine === selection.endLine
      );

      if (existing) {
        // Remove it (toggle off)
        return {
          textSelections: state.textSelections.filter((s) => s.id !== existing.id),
        };
      }

      // Add it (toggle on)
      return {
        textSelections: [
          ...state.textSelections,
          {
            ...selection,
            id: `sel-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            timestamp: Date.now(),
          },
        ],
      };
    }),

  // Persona actions
  setSelectedPersona: (personaId) =>
    set((state) => ({
      selectedPersonaId: personaId,
      // Keep outbound preview persona in sync for Events panel
      outboundPreview: state.outboundPreview
        ? { ...state.outboundPreview, persona_id: personaId, updated_at: Date.now() }
        : state.outboundPreview,
    })),

  // Phase 2: Outbound preview actions
  setOutboundPreview: (preview) =>
    set({
      outboundPreview: {
        ...preview,
        updated_at: Date.now(),
      },
    }),

  clearOutboundPreview: () => set({ outboundPreview: null }),

  bumpConversationRefresh: () =>
    set((state) => ({ conversationRefreshToken: (state.conversationRefreshToken || 0) + 1 })),

  // Editor maximize toggle
  toggleEditorMaximized: () => set((state) => ({ isEditorMaximized: !state.isEditorMaximized })),
}));
