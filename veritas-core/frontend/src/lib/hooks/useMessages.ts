/**
 * Messages Hook (B1.4 - Kill Switch)
 * B1.6 - Updated to use authFetch
 *
 * React Query hooks for message operations.
 * Sets activeRunId on message submit for kill switch support.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/lib/utils/constants";
import { authFetch } from "@/lib/api/authFetch";
import { useWorkbenchStore } from "@/lib/store";
import type { Message, MessageSubmitResponse } from "@/lib/api/types";

// =============================================================================
// API Functions
// =============================================================================

async function fetchMessages(sessionId: string): Promise<Message[]> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}/messages`
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch messages: ${response.statusText}`);
  }

  return response.json();
}

// (Stage 14) Artifact previews are handled server-side in run context; no client-side injection.

async function submitMessage(
  sessionId: string,
  content: string,
  contextCfg?: {
    focused_artifact_ids: string[];
    focus_mode: "prefer" | "only";
    artifact_scope: "session" | "all_sessions";
    external_sources: Record<string, string>;
    // Edit target (B1.7) - AI output should update this artifact
    edit_target_artifact_id?: string | null;
    edit_target_selections?: Array<{
      artifactId: string;
      startLine: number;
      endLine: number;
      text: string;
    }>;
  },
  llmCfg?: {
    llm_provider?: string;
    llm_model?: string;
    llm_strict?: boolean;
  }
): Promise<MessageSubmitResponse> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ content, ...(contextCfg || {}), ...(llmCfg || {}) }),
    }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to submit message: ${response.statusText}`);
  }

  return response.json();
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook to fetch message history for a session.
 */
export function useMessages(sessionId: string | null) {
  const { setMessages } = useWorkbenchStore();

  return useQuery({
    queryKey: ["messages", sessionId],
    queryFn: async () => {
      if (!sessionId) return [];
      const messages = await fetchMessages(sessionId);
      // Sync to store for SSE updates
      setMessages(messages);
      return messages;
    },
    enabled: !!sessionId,
    staleTime: 30000, // 30 seconds
  });
}

/**
 * Hook to submit a message to a session.
 * Sets activeRunId for kill switch support (B1.4).
 */
export function useSendMessage() {
  const queryClient = useQueryClient();
  const { addMessage, currentSessionId, setActiveRun } = useWorkbenchStore();

  return useMutation({
    mutationFn: async ({ content }: { content: string }) => {
      if (!currentSessionId) {
        throw new Error("No session selected");
      }

      // Stage 14: workspace context config is sent as metadata (not injected into message)
      const state = useWorkbenchStore.getState();

      return submitMessage(
        currentSessionId,
        content,
        {
          focused_artifact_ids: state.focusedArtifactIds,
          focus_mode: state.focusMode,
          artifact_scope: state.artifactScope,
          external_sources: state.externalSources,
          // Edit target (B1.7) - AI output should update this artifact
          edit_target_artifact_id: state.editTargetArtifactId,
          edit_target_selections: state.editTargetSelections.map((s) => ({
            artifactId: s.artifactId,
            startLine: s.startLine,
            endLine: s.endLine,
            text: s.text,
          })),
        },
        // LLM selection is handled by the chat UI; default is unset here.
        undefined
      );
    },
    onSuccess: (data) => {
      // Add user message to store immediately
      addMessage(data.user_message);

      // Set active run for kill switch (B1.4)
      // This enables the kill switch button immediately
      setActiveRun(data.run_id);

      // Invalidate messages query to trigger refetch when streaming completes
      if (currentSessionId) {
        queryClient.invalidateQueries({
          queryKey: ["messages", currentSessionId],
        });
      }
    },
  });
}
