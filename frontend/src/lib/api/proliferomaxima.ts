import { authFetch } from "./authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";

export interface ProliferomaximaRunRequest {
  library_path?: string;
  max_files?: number;
  max_items?: number;
  reference_types?: string[];
  year_from?: number;
  year_to?: number;
  paper_ids?: string[];
}

// All available reference types
export const ALL_REFERENCE_TYPES = [
  "journal_article",
  "book",
  "book_chapter",
  "conference",
  "thesis",
  "report",
  "webpage",
  "other",
] as const;

// Default academic types (checked by default)
export const DEFAULT_ACADEMIC_TYPES = [
  "journal_article",
  "book",
  "book_chapter",
  "conference",
  "thesis",
] as const;

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
  already_exists?: number;
  needs_review?: number;
  skipped_non_academic?: number;
  skipped_year_filter?: number;
  filters_applied?: {
    reference_types: string[];
    year_from: number | null;
    year_to: number | null;
  };
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

// Paper search types and functions
export interface PaperSearchItem {
  paper_id: string;
  title: string | null;
  year: number | null;
  journal: string | null;
  authors: string[];
}

export interface PaperSearchResponse {
  papers: PaperSearchItem[];
  total: number;
}

export async function searchPapers(query: string, limit = 50): Promise<PaperSearchResponse> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/proliferomaxima/search-papers`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit }),
  });
  if (!res.ok) throw new Error(`Paper search failed: ${res.status}`);
  return res.json();
}
