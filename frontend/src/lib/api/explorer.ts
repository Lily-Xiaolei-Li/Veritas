/**
 * Explorer API - File browsing and import
 */

import { authFetch } from "./authFetch";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface FileItem {
  name: string;
  type: "file" | "folder";
  path: string;
  size?: number;
  extension?: string;
  modified?: string;
}

export interface DirectoryListing {
  path: string;
  parent: string | null;
  items: FileItem[];
  count: number;
  error?: string;
}

export interface RootDirectory {
  name: string;
  path: string;
  icon: string;
}

export interface ImportedArtifact {
  name: string;
  path: string;
  type: string;
  source: string;
  artifact_id?: string;
  run_id?: string;
}

export interface ImportResult {
  success: boolean;
  run_id?: string;
  artifacts: ImportedArtifact[];
  created_count?: number;
  failed_count?: number;
  source_file?: string;
  error?: string;
  errors?: string[];
}

export interface SupportedType {
  extension: string;
  description: string;
  converts_to: string[];
}

export interface ExplorerCapabilityCheck {
  name: string;
  extensions: string[];
  ok: boolean;
  detail: string;
  remediation?: string | null;
}

export interface ExplorerCapabilities {
  ok: boolean;
  checks: ExplorerCapabilityCheck[];
}

export interface ImportablesResult {
  path: string;
  recursive: boolean;
  count: number;
  files: string[];
}

/**
 * Get common root directories for browsing
 */
export async function getRoots(): Promise<RootDirectory[]> {
  const res = await authFetch(`${API_BASE}/api/v1/explorer/roots`);
  if (!res.ok) {
    throw new Error("Failed to fetch roots");
  }
  const data = await res.json();
  return data.roots;
}

/**
 * Browse a directory
 */
export async function browseDirectory(path: string): Promise<DirectoryListing> {
  const res = await authFetch(
    `${API_BASE}/api/v1/explorer/browse?path=${encodeURIComponent(path)}`
  );
  if (!res.ok) {
    throw new Error("Failed to browse directory");
  }
  return res.json();
}

/**
 * Import a file as artifact(s)
 */
export async function importFile(
  filePath: string,
  sessionId: string
): Promise<ImportResult> {
  const res = await authFetch(`${API_BASE}/api/v1/explorer/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      file_path: filePath,
      session_id: sessionId,
    }),
  });
  if (!res.ok) {
    throw new Error("Failed to import file");
  }
  return res.json();
}

/**
 * Get supported file types
 */
export async function getSupportedTypes(): Promise<SupportedType[]> {
  const res = await authFetch(`${API_BASE}/api/v1/explorer/supported-types`);
  if (!res.ok) {
    throw new Error("Failed to fetch supported types");
  }
  const data = await res.json();
  return data.types;
}

/**
 * Get backend capabilities for conversions
 */
export async function getExplorerCapabilities(): Promise<ExplorerCapabilities> {
  const res = await authFetch(`${API_BASE}/api/v1/explorer/capabilities`);
  if (!res.ok) {
    throw new Error("Failed to fetch explorer capabilities");
  }
  return res.json();
}

export async function getImportables(
  folderPath: string,
  recursive: boolean
): Promise<ImportablesResult> {
  const res = await authFetch(
    `${API_BASE}/api/v1/explorer/importables?path=${encodeURIComponent(
      folderPath
    )}&recursive=${recursive ? "true" : "false"}`
  );
  if (!res.ok) {
    throw new Error("Failed to list importables");
  }
  return res.json();
}

/**
 * Check if a file type is supported for import
 */
export function isImportable(extension: string): boolean {
  const supported = [".docx", ".xlsx", ".xls", ".csv", ".pdf", ".txt", ".md", ".json"];
  return supported.includes(extension.toLowerCase());
}
