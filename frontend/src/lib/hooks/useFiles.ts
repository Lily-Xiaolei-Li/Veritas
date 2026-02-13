/**
 * useFiles Hook (B1.2 - File Browser & Workspace)
 * B1.6 - Updated to use authFetch
 *
 * React Query hooks for file management:
 * - Fetching file list with pagination and filtering
 * - Attaching files to sessions
 * - Detaching files from sessions
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/lib/utils/constants";
import { authFetch } from "@/lib/api/authFetch";
import type {
  FileIndex,
  FileListResponse,
  FileListParams,
  FileAttachment,
  AttachFilesResponse,
} from "@/lib/api/types";

// =============================================================================
// API Functions
// =============================================================================

/**
 * Fetch indexed files from the workspace.
 */
async function fetchFiles(params: FileListParams = {}): Promise<FileListResponse> {
  const searchParams = new URLSearchParams();

  if (params.limit !== undefined) searchParams.set("limit", String(params.limit));
  if (params.offset !== undefined) searchParams.set("offset", String(params.offset));
  if (params.sort) searchParams.set("sort", params.sort);
  if (params.prefix) searchParams.set("prefix", params.prefix);
  if (params.extension) searchParams.set("extension", params.extension);
  if (params.search) searchParams.set("search", params.search);
  if (params.include_deleted) searchParams.set("include_deleted", "true");

  const url = `${API_BASE_URL}/api/v1/files?${searchParams.toString()}`;
  const response = await authFetch(url);

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to fetch files: ${error}`);
  }

  return response.json();
}

/**
 * Fetch a single file by ID.
 */
async function fetchFile(fileId: string): Promise<FileIndex> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/files/${fileId}`);

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to fetch file: ${error}`);
  }

  return response.json();
}

/**
 * Fetch files attached to a session.
 */
async function fetchSessionFiles(sessionId: string): Promise<FileAttachment[]> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}/files`
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to fetch session files: ${error}`);
  }

  return response.json();
}

/**
 * Attach files to a session.
 */
async function attachFilesToSession(
  sessionId: string,
  fileIds: string[]
): Promise<AttachFilesResponse> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}/files`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ file_ids: fileIds }),
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to attach files: ${error}`);
  }

  return response.json();
}

/**
 * Detach a file from a session.
 */
async function detachFileFromSession(
  sessionId: string,
  fileId: string
): Promise<void> {
  const response = await authFetch(
    `${API_BASE_URL}/api/v1/sessions/${sessionId}/files/${fileId}`,
    { method: "DELETE" }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Failed to detach file: ${error}`);
  }
}

// =============================================================================
// React Query Hooks
// =============================================================================

/**
 * Hook for fetching indexed files with pagination and filtering.
 */
export function useFiles(params: FileListParams = {}) {
  return useQuery({
    queryKey: ["files", params],
    queryFn: () => fetchFiles(params),
    staleTime: 30000, // Consider data fresh for 30 seconds
    refetchOnWindowFocus: false, // SSE handles real-time updates
  });
}

/**
 * Hook for fetching a single file.
 */
export function useFile(fileId: string | null) {
  return useQuery({
    queryKey: ["file", fileId],
    queryFn: () => (fileId ? fetchFile(fileId) : null),
    enabled: !!fileId,
  });
}

/**
 * Hook for fetching files attached to a session.
 */
export function useSessionFiles(sessionId: string | null) {
  return useQuery({
    queryKey: ["session-files", sessionId],
    queryFn: () => (sessionId ? fetchSessionFiles(sessionId) : []),
    enabled: !!sessionId,
    staleTime: 30000,
  });
}

/**
 * Hook for attaching files to a session.
 */
export function useAttachFiles() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sessionId,
      fileIds,
    }: {
      sessionId: string;
      fileIds: string[];
    }) => attachFilesToSession(sessionId, fileIds),
    onSuccess: (_, { sessionId }) => {
      // Invalidate session files cache to refetch
      queryClient.invalidateQueries({ queryKey: ["session-files", sessionId] });
    },
  });
}

/**
 * Hook for detaching a file from a session.
 */
export function useDetachFile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sessionId,
      fileId,
    }: {
      sessionId: string;
      fileId: string;
    }) => detachFileFromSession(sessionId, fileId),
    onSuccess: (_, { sessionId }) => {
      // Invalidate session files cache to refetch
      queryClient.invalidateQueries({ queryKey: ["session-files", sessionId] });
    },
  });
}

/**
 * Helper to invalidate file queries (call after SSE file events).
 */
export function useInvalidateFiles() {
  const queryClient = useQueryClient();

  return {
    invalidateFileList: () => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
    },
    invalidateFile: (fileId: string) => {
      queryClient.invalidateQueries({ queryKey: ["file", fileId] });
    },
    invalidateAll: () => {
      queryClient.invalidateQueries({ queryKey: ["files"] });
    },
  };
}
