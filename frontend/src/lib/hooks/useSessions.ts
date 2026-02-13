/**
 * Sessions Hook (B1.1 - Streaming Reasoning & Events)
 * B1.6 - Updated to use authFetch
 *
 * React Query hooks for session operations.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/lib/utils/constants";
import { authFetch } from "@/lib/api/authFetch";
import { useWorkbenchStore } from "@/lib/store";
import type { Session, SessionCreate, SessionUpdate } from "@/lib/api/types";

// =============================================================================
// API Functions
// =============================================================================

async function fetchSessions(): Promise<Session[]> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/sessions`);

  if (!response.ok) {
    throw new Error(`Failed to fetch sessions: ${response.statusText}`);
  }

  return response.json();
}

async function createSession(data: SessionCreate): Promise<Session> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/sessions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create session: ${response.statusText}`);
  }

  return response.json();
}

async function deleteSession(sessionId: string): Promise<void> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete session: ${response.statusText}`);
  }
}

async function updateSession({
  sessionId,
  data,
}: {
  sessionId: string;
  data: SessionUpdate;
}): Promise<Session> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to update session: ${response.statusText}`);
  }

  return response.json();
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook to fetch all sessions.
 */
export function useSessions() {
  return useQuery({
    queryKey: ["sessions"],
    queryFn: fetchSessions,
    staleTime: 60000, // 1 minute
  });
}

/**
 * Hook to create a new session.
 */
export function useCreateSession() {
  const queryClient = useQueryClient();
  const { setCurrentSession } = useWorkbenchStore();

  return useMutation({
    mutationFn: createSession,
    onSuccess: (session) => {
      // Invalidate sessions list
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      // Set as current session
      setCurrentSession(session.id);
    },
  });
}

/**
 * Hook to delete a session.
 */
export function useDeleteSession() {
  const queryClient = useQueryClient();
  const { currentSessionId, setCurrentSession } = useWorkbenchStore();

  return useMutation({
    mutationFn: deleteSession,
    onSuccess: (_, deletedId) => {
      // Invalidate sessions list
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      // If deleted current session, clear selection
      if (currentSessionId === deletedId) {
        setCurrentSession(null);
      }
    },
  });
}

/**
 * Hook to update a session (rename).
 */
export function useUpdateSession() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateSession,
    onSuccess: () => {
      // Invalidate sessions list
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });
}
