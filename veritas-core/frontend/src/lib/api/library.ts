/**
 * Library Tools API Client
 * 
 * API functions for library database status, integrity check, gap analysis, and export.
 */

import { authFetch } from "./authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";

const LIBRARY_BASE = `${API_BASE_URL}/api/v1/library`;

// Types

export interface LibraryStatus {
  total_papers: number;
  parsed_count: number;
  has_chunks: number;
  completeness_pct: number;
  in_vf_store: number;
  section_coverage: Record<string, string>;
  last_updated: string;
}

export interface LibraryCheck {
  ok: boolean;
  total_papers: number;
  missing_chunks: number;
  missing_vectors: number;
  issues: string[];
  recommendations: string[];
}

export interface LibraryGaps {
  total_papers: number;
  missing_sections: Record<string, number>;
  incomplete_papers: Array<{
    paper_id: string;
    missing: string[];
    completeness: number;
  }>;
  coverage_by_year: Record<string, number>;
  priority_gaps: Array<{
    section: string;
    missing_count: number;
  }>;
}

export interface QuickStats {
  total: number;
  completeness_pct: number;
  vf_count: number;
}

// API Functions

export async function fetchLibraryStatus(): Promise<LibraryStatus> {
  const res = await authFetch(`${LIBRARY_BASE}/status`);
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function fetchLibraryCheck(): Promise<LibraryCheck> {
  const res = await authFetch(`${LIBRARY_BASE}/check`);
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function fetchLibraryGaps(): Promise<LibraryGaps> {
  const res = await authFetch(`${LIBRARY_BASE}/gaps`);
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function fetchQuickStats(): Promise<QuickStats> {
  const res = await authFetch(`${LIBRARY_BASE}/quick-stats`);
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function downloadLibraryExport(format: "csv" | "json" = "csv"): Promise<void> {
  const res = await authFetch(`${LIBRARY_BASE}/export?format=${format}`);
  if (!res.ok) {
    throw new Error(await res.text());
  }
  
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `library_export.${format}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
