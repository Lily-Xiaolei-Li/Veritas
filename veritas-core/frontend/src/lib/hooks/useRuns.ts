/**
 * Run History Hook (B2.1)
 *
 * Provides run list fetching and resume functionality for sessions.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authFetch } from "@/lib/api/authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";
import type {
  Run,
  RunListResponse,
  ResumeResponse,
  RunListParams,
} from "@/lib/api/types";

/**
 * Fetch runs for a session
 */
async function fetchRuns(
  sessionId: string,
  params: RunListParams = {}
): Promise<RunListResponse> {
  const searchParams = new URLSearchParams();
  if (params.limit) searchParams.set("limit", String(params.limit));
  if (params.offset) searchParams.set("offset", String(params.offset));

  const url = `${API_BASE_URL}/api/v1/sessions/${sessionId}/runs?${searchParams}`;
  const response = await authFetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch runs: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch a single run by ID
 */
async function fetchRun(runId: string): Promise<Run> {
  const url = `${API_BASE_URL}/api/v1/runs/${runId}`;
  const response = await authFetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch run: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Resume a run
 */
async function resumeRun(runId: string): Promise<ResumeResponse> {
  const url = `${API_BASE_URL}/api/v1/runs/${runId}/resume`;
  const response = await authFetch(url, {
    method: "POST",
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to resume run: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Hook for fetching run list for a session
 */
export function useRuns(sessionId: string | null, params: RunListParams = {}) {
  return useQuery({
    queryKey: ["runs", sessionId, params],
    queryFn: () => fetchRuns(sessionId!, params),
    enabled: !!sessionId,
    refetchInterval: 5000, // Poll every 5 seconds for status updates
  });
}

/**
 * Hook for fetching a single run
 */
export function useRun(runId: string | null) {
  return useQuery({
    queryKey: ["run", runId],
    queryFn: () => fetchRun(runId!),
    enabled: !!runId,
  });
}

/**
 * Hook for resuming a run
 */
export function useResumeRun() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: resumeRun,
    onSuccess: (data, runId) => {
      // Invalidate run queries to refresh status
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      queryClient.invalidateQueries({ queryKey: ["run", runId] });
    },
  });
}

/**
 * Check if a run can be resumed
 */
export function canResumeRun(run: Run): boolean {
  const resumableStatuses = ["terminated", "failed", "interrupted"];
  return resumableStatuses.includes(run.status) && run.has_checkpoints;
}

/**
 * Get human-readable status label
 */
export function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: "Pending",
    running: "Running",
    completed: "Completed",
    failed: "Failed",
    terminated: "Terminated",
    interrupted: "Interrupted",
  };
  return labels[status] || status;
}

/**
 * Get status badge color class
 */
export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: "bg-gray-500",
    running: "bg-blue-500",
    completed: "bg-green-500",
    failed: "bg-red-500",
    terminated: "bg-yellow-500",
    interrupted: "bg-orange-500",
  };
  return colors[status] || "bg-gray-500";
}
