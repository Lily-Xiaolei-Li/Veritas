/**
 * Paper Download API Client
 *
 * Provides functions to interact with the paper download endpoints.
 */

import { authFetch } from "./authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";

const PAPERS_BASE = `${API_BASE_URL}/api/v1/papers`;

// =============================================================================
// Types
// =============================================================================

export interface SingleDownloadRequest {
  doi?: string;
  title?: string;
  use_ezproxy?: boolean;
}

export interface SingleDownloadResponse {
  doi: string;
  title: string;
  status: string;
  source: string;
  file_path: string;
  file_size: number;
  error: string;
}

export interface BatchDownloadRequest {
  dois: string[];
  use_ezproxy?: boolean;
}

export interface BatchDownloadResponse {
  job_id: string;
  status: string;
  total: number;
  message: string;
}

export interface BatchStatusResponse {
  job_id: string;
  status: string;
  total: number;
  completed: number;
  success: number;
  failed: number;
  results: PaperResult[];
}

export interface PaperResult {
  doi: string;
  title: string;
  author: string;
  year: string;
  status: string;
  source: string;
  file_path: string;
  file_size: number;
  error: string;
}

export interface DownloadedFile {
  filename: string;
  size: number;
  path: string;
}

// =============================================================================
// API Functions
// =============================================================================

export async function downloadPaper(req: SingleDownloadRequest): Promise<SingleDownloadResponse> {
  const res = await authFetch(`${PAPERS_BASE}/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Download failed: ${res.statusText}`);
  return res.json();
}

export async function startBatchDownload(req: BatchDownloadRequest): Promise<BatchDownloadResponse> {
  const res = await authFetch(`${PAPERS_BASE}/batch-download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`Batch download failed: ${res.statusText}`);
  return res.json();
}

export async function getBatchStatus(jobId: string): Promise<BatchStatusResponse> {
  const res = await authFetch(`${PAPERS_BASE}/batch-download/${jobId}`);
  if (!res.ok) throw new Error(`Failed to get batch status: ${res.statusText}`);
  return res.json();
}

export async function importCsv(file: File): Promise<BatchDownloadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await authFetch(`${PAPERS_BASE}/import-csv`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`CSV import failed: ${res.statusText}`);
  return res.json();
}

export async function listDownloads(): Promise<DownloadedFile[]> {
  const res = await authFetch(`${PAPERS_BASE}/downloads`);
  if (!res.ok) throw new Error(`Failed to list downloads: ${res.statusText}`);
  return res.json();
}
