/**
 * Kill Switch Hook (B1.4)
 *
 * Provides mutation for terminating the active run in a session.
 */

import { useMutation } from "@tanstack/react-query";
import { authFetch } from "@/lib/api/authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";
import { useWorkbenchStore } from "@/lib/store";
import type { TerminateResponse } from "@/lib/api/types";

/**
 * Terminate the active run for a session.
 */
async function terminateSession(sessionId: string): Promise<TerminateResponse> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}/terminate`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `Failed to terminate: ${response.status}`);
  }

  return response.json();
}

/**
 * Hook for kill switch functionality.
 *
 * Usage:
 * ```tsx
 * const { terminate, isTerminating } = useKillSwitch();
 * <button onClick={terminate} disabled={isTerminating}>Stop</button>
 * ```
 */
export function useKillSwitch() {
  const {
    currentSessionId,
    executionStatus,
    setTerminating,
    markTerminated,
    setSSEError,
  } = useWorkbenchStore();

  const mutation = useMutation({
    mutationFn: async () => {
      if (!currentSessionId) {
        throw new Error("No active session");
      }
      return terminateSession(currentSessionId);
    },

    onMutate: () => {
      // Optimistic update - set terminating state immediately
      setTerminating();
    },

    onSuccess: (data) => {
      // If SSE event comes through, it will handle the state update
      // But if no active run was found, we need to clear state here
      if (data.status === "no_active_run") {
        markTerminated({
          reason: "user_cancel",
          message: data.message || "No active run to terminate",
        });
      }
      // For "terminated" status, the SSE event will update the state
    },

    onError: (error: Error) => {
      setSSEError(`Kill switch failed: ${error.message}`);
    },
  });

  return {
    /** Trigger termination of active run */
    terminate: mutation.mutate,
    /** Whether termination is in progress */
    isTerminating: executionStatus === "terminating" || mutation.isPending,
    /** Whether kill switch can be used (has active run) */
    canTerminate:
      currentSessionId !== null &&
      (executionStatus === "running" || executionStatus === "terminating"),
    /** Any error from the mutation */
    error: mutation.error,
  };
}
