import { authFetch, authPost } from "@/lib/api/authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";

export interface WorkspaceSaveResponse {
  session_id: string;
  saved_at: string;
  workspace_state_version: number;
}

export interface UndoStackItem {
  id: string;
  action_type: "artifact_delete" | "session_delete";
  target_id: string;
  created_at: string;
}

export interface UndoStackResponse {
  items: UndoStackItem[];
}

export interface UndoResponse {
  ok: boolean;
  undone_action_id?: string | null;
  action_type?: string | null;
  target_id?: string | null;
}

export async function saveWorkspace(sessionId: string): Promise<WorkspaceSaveResponse> {
  const resp = await authPost(`${API_BASE_URL}/api/v1/workspace/save`, { session_id: sessionId });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `HTTP ${resp.status}`);
  }
  return (await resp.json()) as WorkspaceSaveResponse;
}

export async function getUndoStack(sessionId: string): Promise<UndoStackResponse> {
  const resp = await authFetch(`${API_BASE_URL}/api/v1/workspace/undo-stack?session_id=${encodeURIComponent(sessionId)}`, {
    method: "GET",
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `HTTP ${resp.status}`);
  }
  return (await resp.json()) as UndoStackResponse;
}

export async function undoLatest(sessionId: string): Promise<UndoResponse> {
  const resp = await authPost(`${API_BASE_URL}/api/v1/workspace/undo`, { session_id: sessionId });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `HTTP ${resp.status}`);
  }
  return (await resp.json()) as UndoResponse;
}

export async function exportWorkspace(sessionId: string): Promise<Blob> {
  const resp = await authFetch(`${API_BASE_URL}/api/v1/workspace/export?session_id=${encodeURIComponent(sessionId)}`, {
    method: "GET",
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `HTTP ${resp.status}`);
  }
  return await resp.blob();
}

export async function importWorkspace(data: unknown, mode: "merge" | "replace"): Promise<{ ok: boolean; imported_session_id?: string; imported_messages?: number; imported_artifacts?: number }> {
  const resp = await authPost(`${API_BASE_URL}/api/v1/workspace/import`, { data, mode });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `HTTP ${resp.status}`);
  }
  return (await resp.json()) as { ok: boolean; imported_session_id?: string; imported_messages?: number; imported_artifacts?: number };
}

export interface ResetWorkspaceResponse {
  ok: boolean;
  deleted_sessions: number;
  deleted_artifacts: number;
  deleted_messages: number;
}

export async function resetWorkspace(): Promise<ResetWorkspaceResponse> {
  const resp = await authPost(`${API_BASE_URL}/api/v1/workspace/reset`, {});
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `HTTP ${resp.status}`);
  }
  return (await resp.json()) as ResetWorkspaceResponse;
}
