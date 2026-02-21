/**
 * Local/Combined Artifact Types
 */

import type { Artifact, ArtifactPreviewKind, ArtifactType } from "@/lib/api/types";

export interface LocalArtifact {
  id: string;
  run_id: string;
  session_id: string;
  display_name: string;
  storage_path: string;
  extension: string | null;
  size_bytes: number;
  content_hash: string | null;
  mime_type: string | null;
  artifact_type: ArtifactType;
  created_at: string;
  artifact_meta: Record<string, unknown> | null;
  is_deleted: boolean;
  can_preview: boolean;
  preview_kind: ArtifactPreviewKind;
  download_url: string;
  source: "chat";
  content: string;
  filename?: string;
}

export type ArtifactLike = Artifact | LocalArtifact;

export function isLocalArtifact(artifact: ArtifactLike): artifact is LocalArtifact {
  return (artifact as LocalArtifact).source === "chat";
}
