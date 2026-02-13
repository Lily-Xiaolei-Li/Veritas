/**
 * useArtifacts Hook (B1.3 - Artifact Handling)
 * B1.6 - Updated to use authFetch
 *
 * React Query hooks for artifact management:
 * - Fetching artifact list by session or run
 * - Fetching single artifact metadata
 * - Fetching artifact preview
 * - Download URL helpers
 */

import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/lib/utils/constants";
import { authFetch } from "@/lib/api/authFetch";
import type {
  Artifact,
  ArtifactListResponse,
  ArtifactListParams,
  ArtifactPreview,
} from "@/lib/api/types";

export interface ArtifactDraft {
  artifact_id: string;
  session_id: string;
  is_draft: boolean;
  draft_content: string | null;
  draft_updated_at: string | null;
}

// =============================================================================
// API Functions
// =============================================================================

/**
 * Fetch artifacts for a session with pagination and filtering.
 */
async function fetchSessionArtifacts(
  sessionId: string,
  params: ArtifactListParams = {}
): Promise<ArtifactListResponse> {
  const searchParams = new URLSearchParams();

  if (params.limit !== undefined) searchParams.set("limit", String(params.limit));
  if (params.offset !== undefined) searchParams.set("offset", String(params.offset));
  if (params.sort) searchParams.set("sort", params.sort);
  if (params.artifact_type) searchParams.set("artifact_type", params.artifact_type);
  if (params.extension) searchParams.set("extension", params.extension);
  if (params.include_deleted) searchParams.set("include_deleted", "true");

  const url = `${API_BASE_URL}/api/v1/sessions/${sessionId}/artifacts?${searchParams.toString()}`;
  const response = await authFetch(url);

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to fetch artifacts: ${error}`);
  }

  return response.json();
}

/**
 * Fetch artifacts for a run with pagination and filtering.
 */
async function fetchRunArtifacts(
  runId: string,
  params: ArtifactListParams = {}
): Promise<ArtifactListResponse> {
  const searchParams = new URLSearchParams();

  if (params.limit !== undefined) searchParams.set("limit", String(params.limit));
  if (params.offset !== undefined) searchParams.set("offset", String(params.offset));
  if (params.sort) searchParams.set("sort", params.sort);
  if (params.artifact_type) searchParams.set("artifact_type", params.artifact_type);
  if (params.include_deleted) searchParams.set("include_deleted", "true");

  const url = `${API_BASE_URL}/api/v1/runs/${runId}/artifacts?${searchParams.toString()}`;
  const response = await authFetch(url);

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to fetch artifacts: ${error}`);
  }

  return response.json();
}

/**
 * Fetch a single artifact by ID.
 */
async function fetchArtifact(artifactId: string): Promise<Artifact> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/artifacts/${artifactId}`);

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to fetch artifact: ${error}`);
  }

  return response.json();
}

/**
 * Fetch artifact preview content.
 */
async function fetchArtifactPreview(artifactId: string): Promise<ArtifactPreview> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/artifacts/${artifactId}/preview`
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to fetch preview: ${error}`);
  }

  return response.json();
}

/**
 * Fetch artifact draft content (Phase 1).
 */
async function fetchArtifactDraft(artifactId: string): Promise<ArtifactDraft> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/artifacts/${artifactId}/draft`
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to fetch draft: ${error}`);
  }

  return response.json();
}

/**
 * Update artifact draft content (Phase 1).
 */
async function updateArtifactDraftApi(params: {
  artifactId: string;
  draftContent: string;
  isAutoSave?: boolean;
  clear?: boolean;
}): Promise<ArtifactDraft> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/artifacts/${params.artifactId}/draft`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        draft_content: params.draftContent,
        clear: params.clear ?? false,
        is_auto_save: params.isAutoSave ?? true,
      }),
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to update draft: ${error}`);
  }

  return response.json();
}

/**
 * Soft-delete an artifact.
 */
async function deleteArtifact(artifactId: string): Promise<void> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/artifacts/${artifactId}`,
    { method: "DELETE" }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to delete artifact: ${error}`);
  }
}

/**
 * Create (save) a new artifact under a session.
 * Stage 8: used for persisting edited local artifacts.
 */
async function createSessionArtifact(
  sessionId: string,
  filename: string,
  content: string,
  opts?: { sourceArtifactId?: string; artifactMeta?: Record<string, unknown> }
): Promise<Artifact> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}/artifacts`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename,
        content,
        artifact_type: "file",
        artifact_meta: opts?.artifactMeta || null,
        source_artifact_id: opts?.sourceArtifactId || null,
      }),
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to save artifact: ${error}`);
  }

  return response.json();
}

/**
 * Update content of an existing artifact.
 */
async function updateArtifactContent(
  artifactId: string,
  content: string
): Promise<Artifact> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/artifacts/${artifactId}/content`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to update artifact: ${error}`);
  }

  return response.json();
}

// =============================================================================
// React Query Hooks
// =============================================================================

/**
 * Hook for fetching artifacts for a session.
 */
export function useSessionArtifacts(
  sessionId: string | null,
  params: ArtifactListParams = {}
) {
  return useQuery({
    queryKey: ["session-artifacts", sessionId, params],
    queryFn: () => (sessionId ? fetchSessionArtifacts(sessionId, params) : null),
    enabled: !!sessionId,
    staleTime: 30000, // Consider data fresh for 30 seconds
    refetchOnWindowFocus: false, // SSE handles real-time updates
  });
}

/**
 * Hook for fetching artifacts for a run.
 */
export function useRunArtifacts(
  runId: string | null,
  params: ArtifactListParams = {}
) {
  return useQuery({
    queryKey: ["run-artifacts", runId, params],
    queryFn: () => (runId ? fetchRunArtifacts(runId, params) : null),
    enabled: !!runId,
    staleTime: 30000,
    refetchOnWindowFocus: false,
  });
}

/**
 * Hook for fetching a single artifact.
 */
export function useArtifact(artifactId: string | null) {
  return useQuery({
    queryKey: ["artifact", artifactId],
    queryFn: () => (artifactId ? fetchArtifact(artifactId) : null),
    enabled: !!artifactId,
  });
}

/**
 * Hook for fetching artifact preview.
 */
export function useArtifactPreview(artifactId: string | null) {
  return useQuery({
    queryKey: ["artifact-preview", artifactId],
    queryFn: () => (artifactId ? fetchArtifactPreview(artifactId) : null),
    enabled: !!artifactId,
    staleTime: 60000, // Previews don't change, cache longer
  });
}

/**
 * Hook for fetching artifact draft content.
 */
export function useArtifactDraft(artifactId: string | null) {
  return useQuery({
    queryKey: ["artifact-draft", artifactId],
    queryFn: () => (artifactId ? fetchArtifactDraft(artifactId) : null),
    enabled: !!artifactId,
    staleTime: 0,
  });
}

/**
 * Hook for updating artifact draft content.
 */
export function useUpdateArtifactDraft() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (args: {
      artifactId: string;
      draftContent: string;
      isAutoSave?: boolean;
      clear?: boolean;
    }) => updateArtifactDraftApi(args),
    onSuccess: (draft) => {
      queryClient.setQueryData(["artifact-draft", draft.artifact_id], draft);
    },
  });
}

/**
 * Hook for deleting an artifact.
 */
export function useDeleteArtifact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (artifactId: string) => deleteArtifact(artifactId),
    onSuccess: () => {
      // Invalidate all artifact queries to refetch
      queryClient.invalidateQueries({ queryKey: ["session-artifacts"] });
      queryClient.invalidateQueries({ queryKey: ["run-artifacts"] });
    },
  });
}

/**
 * Save edited content as a new artifact.
 */
export function useSaveArtifact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (args: {
      sessionId: string;
      filename: string;
      content: string;
      sourceArtifactId?: string;
      artifactMeta?: Record<string, unknown>;
    }) =>
      createSessionArtifact(args.sessionId, args.filename, args.content, {
        sourceArtifactId: args.sourceArtifactId,
        artifactMeta: args.artifactMeta,
      }),
    onSuccess: (artifact) => {
      // refresh lists so new artifact appears
      queryClient.invalidateQueries({ queryKey: ["session-artifacts", artifact.session_id] });
      queryClient.invalidateQueries({ queryKey: ["run-artifacts", artifact.run_id] });
    },
  });
}

/**
 * Update content of an existing artifact in-place.
 */
export function useUpdateArtifactContent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (args: { artifactId: string; content: string }) =>
      updateArtifactContent(args.artifactId, args.content),
    onSuccess: (artifact) => {
      // Invalidate preview cache so it refetches
      queryClient.invalidateQueries({ queryKey: ["artifact-preview", artifact.id] });
      // Also invalidate the artifact metadata
      queryClient.invalidateQueries({ queryKey: ["artifact", artifact.id] });
      // Refresh lists to update size etc
      queryClient.invalidateQueries({ queryKey: ["session-artifacts", artifact.session_id] });
    },
  });
}

// =============================================================================
// URL Helpers
// =============================================================================

import { getAuthenticatedSSEUrl } from "@/lib/api/authFetch";

/**
 * Get download URL for a single artifact.
 * Use this with <a href={url} download> for browser-native download.
 * Includes auth token in query string when authenticated.
 */
export function getArtifactDownloadUrl(artifactId: string): string {
  const baseUrl = `${API_BASE_URL}/api/v1/artifacts/${artifactId}/content`;
  return getAuthenticatedSSEUrl(baseUrl);
}

/**
 * Get ZIP download URL for all artifacts in a run.
 * Use this with <a href={url} download> for browser-native download.
 * Includes auth token in query string when authenticated.
 */
export function getRunZipDownloadUrl(runId: string): string {
  const baseUrl = `${API_BASE_URL}/api/v1/runs/${runId}/artifacts/zip`;
  return getAuthenticatedSSEUrl(baseUrl);
}

// =============================================================================
// Cache Helpers
// =============================================================================

/**
 * Helper to add an artifact to the cache (call on SSE artifact_created).
 * Uses incremental update instead of full invalidation.
 */
export function useArtifactCacheHelpers() {
  const queryClient = useQueryClient();

  const addArtifact = React.useCallback(
    (artifact: Artifact) => {
      queryClient.setQueryData<ArtifactListResponse | null>(
        ["session-artifacts", artifact.session_id, {}],
        (old) => {
          if (!old) return null;
          return {
            ...old,
            artifacts: [artifact, ...old.artifacts],
            total: old.total + 1,
          };
        }
      );

      queryClient.setQueryData<ArtifactListResponse | null>(
        ["run-artifacts", artifact.run_id, {}],
        (old) => {
          if (!old) return null;
          return {
            ...old,
            artifacts: [artifact, ...old.artifacts],
            total: old.total + 1,
          };
        }
      );
    },
    [queryClient]
  );

  const removeArtifact = React.useCallback(
    (args: { artifactId: string; sessionId: string; runId: string }) => {
      queryClient.setQueryData<ArtifactListResponse | null>(
        ["session-artifacts", args.sessionId, {}],
        (old) => {
          if (!old) return null;
          const next = old.artifacts.filter((a) => a.id !== args.artifactId);
          return {
            ...old,
            artifacts: next,
            total: Math.max(0, old.total - (next.length === old.artifacts.length ? 0 : 1)),
          };
        }
      );

      queryClient.setQueryData<ArtifactListResponse | null>(
        ["run-artifacts", args.runId, {}],
        (old) => {
          if (!old) return null;
          const next = old.artifacts.filter((a) => a.id !== args.artifactId);
          return {
            ...old,
            artifacts: next,
            total: Math.max(0, old.total - (next.length === old.artifacts.length ? 0 : 1)),
          };
        }
      );
    },
    [queryClient]
  );

  const invalidateAll = React.useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["session-artifacts"] });
    queryClient.invalidateQueries({ queryKey: ["run-artifacts"] });
    queryClient.invalidateQueries({ queryKey: ["artifact"] });
  }, [queryClient]);

  const invalidateSession = React.useCallback(
    (sessionId: string) => {
      queryClient.invalidateQueries({ queryKey: ["session-artifacts", sessionId] });
    },
    [queryClient]
  );

  const invalidateRun = React.useCallback(
    (runId: string) => {
      queryClient.invalidateQueries({ queryKey: ["run-artifacts", runId] });
    },
    [queryClient]
  );

  // Important: return a stable object so consumers can safely use it in deps.
  return React.useMemo(
    () => ({ addArtifact, removeArtifact, invalidateAll, invalidateSession, invalidateRun }),
    [addArtifact, removeArtifact, invalidateAll, invalidateSession, invalidateRun]
  );
}
