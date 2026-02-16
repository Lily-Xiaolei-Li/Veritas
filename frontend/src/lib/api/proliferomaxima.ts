import { authFetch } from "./authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";

export interface ProliferomaximaRunRequest {
  library_path?: string;
  max_files?: number;
  max_items?: number;
}

export interface ProliferomaximaProgress {
  current: number;
  total: number;
  step: string;
}

export interface ProliferomaximaSummary {
  total_refs: number;
  added: number;
  skipped: number;
  failed: number;
  duplicates: number;
}

export async function startProliferomaximaRun(payload: ProliferomaximaRunRequest): Promise<{ run_id: string; status: string }> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/proliferomaxima/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Proliferomaxima run failed: ${res.status}`);
  return res.json();
}

export async function getProliferomaximaStatus(runId: string): Promise<{ run_id: string; status: string; progress?: ProliferomaximaProgress | null; error?: string | null }> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/proliferomaxima/status/${runId}`);
  if (!res.ok) throw new Error(`Proliferomaxima status failed: ${res.status}`);
  return res.json();
}

export async function getProliferomaximaResults(runId: string): Promise<{ run_id: string; status: string; results: ProliferomaximaSummary | null }> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/proliferomaxima/results/${runId}`);
  if (!res.ok && res.status !== 202) throw new Error(`Proliferomaxima results failed: ${res.status}`);
  return res.json();
}
