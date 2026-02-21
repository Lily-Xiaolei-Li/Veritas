import { authFetch } from "./authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";

export type CitalioAction = "auto_cite" | "maybe_cite" | "manual_needed" | "no_cite_needed";

export interface CitalioCandidate {
  paper_id: string;
  authors: string[];
  year?: number;
  title: string;
  cited_for?: string;
  relevance_score: number;
  confidence: number;
  reason: string;
  citation_text: string;
}

export interface CitalioSentenceResult {
  id: string;
  sentence_id: number;
  text: string;
  classification: string;
  action: CitalioAction;
  candidates: CitalioCandidate[];
  suggested_text: string;
  start_offset: number;
  end_offset: number;
}

export interface CitalioSummary {
  total_sentences: number;
  cite_needed: number;
  auto_cited: number;
  maybe_cited: number;
  manual_needed: number;
  no_cite_needed: number;
}

export interface CitalioResults {
  run_id: string;
  status: string;
  session_id?: string;
  timestamp: string;
  summary: CitalioSummary;
  sentences: CitalioSentenceResult[];
}

export async function startCitalioRun(payload: {
  text: string;
  session_id?: string;
  options?: {
    min_confidence?: number;
    max_citations_per_sentence?: number;
    include_common_knowledge?: boolean;
  };
}): Promise<{ run_id: string; status: string }> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/citalio/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Citalio run failed: ${res.status}`);
  return res.json();
}

export async function getCitalioStatus(runId: string): Promise<{ run_id: string; status: string; progress?: { current: number; total: number; step: string } | null; error?: string | null }> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/citalio/status/${runId}`);
  if (!res.ok) throw new Error(`Citalio status failed: ${res.status}`);
  return res.json();
}

export async function getCitalioResults(runId: string): Promise<{ run_id: string; status: string; results: CitalioResults | null }> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/citalio/results/${runId}`);
  if (!res.ok && res.status !== 202) throw new Error(`Citalio results failed: ${res.status}`);
  return res.json();
}

// ============================================================================
// MANUAL MODE - Citalio 手动模式
// ============================================================================

export interface CitalioManualFilters {
  year_min?: number;
  year_max?: number;
  paper_type?: string;
  primary_method?: string;
  keywords?: string[];
  journal?: string;
  authors?: string[];
  in_library?: boolean;
  empirical_context?: string;
}

export interface CitalioManualResult {
  paper_id: string;
  authors: string[];
  year?: number;
  title: string;
  journal?: string;
  matched_chunk_type: string;
  matched_text: string;
  relevance_score: number;
  cite_intext: string;
  cite_full: string;
  meta: Record<string, unknown>;
}

export interface CitalioManualSearchResponse {
  query: string;
  results: CitalioManualResult[];
  total_found: number;
  filters_applied: Record<string, unknown>;
}

export interface CitalioFilterOptions {
  paper_types: string[];
  primary_methods: string[];
  journals: string[];
  year_range: { min: number | null; max: number | null };
  empirical_contexts: string[];
  chunk_types: string[];
}

export async function citalioManualSearch(payload: {
  query: string;
  chunk_types?: string[];
  limit?: number;
  filters?: CitalioManualFilters;
}): Promise<CitalioManualSearchResponse> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/citalio/manual/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Citalio manual search failed: ${res.status}`);
  return res.json();
}

export async function getCitalioFilterOptions(): Promise<CitalioFilterOptions> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/citalio/manual/filter-options`);
  if (!res.ok) throw new Error(`Citalio filter options failed: ${res.status}`);
  return res.json();
}
