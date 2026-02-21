/**
 * Checker API client — calls backend /api/v1/checker/* endpoints.
 */

import { authFetch } from "./authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";

// ── Types ────────────────────────────────────────────────────────────────────

export interface CheckerAnnotation {
  sentence_id: number;
  start_offset: number;
  end_offset: number;
  text: string;
  type: "CITE_NEEDED" | "COMMON" | "OWN_EMPIRICAL" | "OWN_CONTRIBUTION";
  confidence: "HIGH" | "MEDIUM" | "LOW";
  colour: string;
  reasoning: string;
  suggested_citations: { ref: string; source: string; relevance?: number; snippet?: string }[];
  existing_citations_status: { citation: string; status: string; note: string }[];
  ai_flags: { pattern: string; matched: string; note: string; severity: string }[];
  flow: { prev: string | null; suggestion: string | null; topic_shift: boolean };
}

export interface CheckerSummary {
  total_sentences: number;
  cite_needed: number;
  common: number;
  own_empirical: number;
  own_contribution: number;
  ai_patterns: number;
  flow_issues: number;
  misattributed: number;
  verified_citations: number;
}

export interface CheckerResults {
  artifact_id: string;
  run_id: string;
  timestamp: string;
  summary: CheckerSummary;
  annotations: CheckerAnnotation[];
}

export interface CheckerRunOptions {
  check_citations?: boolean;
  check_ai?: boolean;
  check_flow?: boolean;
}

// ── API calls ────────────────────────────────────────────────────────────────

export async function startCheckerRun(
  text: string,
  artifactId?: string,
  options?: CheckerRunOptions
): Promise<{ run_id: string; status: string }> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/checker/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, artifact_id: artifactId, options }),
  });
  if (!res.ok) throw new Error(`Checker run failed: ${res.status}`);
  return res.json();
}

export async function getCheckerStatus(
  runId: string
): Promise<{ run_id: string; status: string; progress?: { current: number; total: number; step: string } | null; error?: string | null }> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/checker/status/${runId}`);
  if (!res.ok) throw new Error(`Checker status failed: ${res.status}`);
  return res.json();
}

export async function getCheckerResults(
  runId: string
): Promise<{ run_id: string; status: string; results: CheckerResults | null }> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/checker/results/${runId}`);
  if (!res.ok && res.status !== 202) throw new Error(`Checker results failed: ${res.status}`);
  return res.json();
}
