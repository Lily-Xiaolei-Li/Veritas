/**
 * Documents API (B1.7 - Document Processing)
 *
 * Upload local documents (from browser) and convert them into artifacts.
 */

import { authFetch } from "./authFetch";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface UploadDocumentResult {
  success: boolean;
  run_id?: string;
  artifacts: Array<{
    artifact_id: string;
    run_id: string;
    name: string;
    extension?: string | null;
    download_url: string;
  }>;
  created_count?: number;
  failed_count?: number;
  source_file?: string;
  errors?: string[];
}

export async function uploadDocument(args: {
  sessionId: string;
  file: File;
}): Promise<UploadDocumentResult> {
  const form = new FormData();
  form.append("session_id", args.sessionId);
  form.append("file", args.file, args.file.name);

  const res = await authFetch(`${API_BASE}/api/v1/documents/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Failed to upload document");
  }

  return res.json();
}
