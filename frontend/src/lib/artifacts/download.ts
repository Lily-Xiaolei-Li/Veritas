/**
 * Artifact download helpers.
 */

import type { ArtifactLike } from "@/lib/artifacts/types";
import { isLocalArtifact } from "@/lib/artifacts/types";

function sanitizeFilename(name: string): string {
  return name
    .replace(/[<>:"/\\|?*\x00-\x1F]/g, "_")
    .replace(/\s+/g, "_")
    .slice(0, 180)
    .trim();
}

export function toMarkdownFilename(name: string): string {
  const trimmed = name.trim();
  const base = trimmed.length > 0 ? trimmed : "artifact";
  const withoutExt = base.replace(/\.[^/.]+$/, "");
  const safe = sanitizeFilename(withoutExt) || "artifact";
  return safe.endsWith(".md") ? safe : `${safe}.md`;
}

export function getArtifactMarkdownName(artifact: ArtifactLike): string {
  if (isLocalArtifact(artifact) && artifact.filename) {
    return toMarkdownFilename(artifact.filename);
  }
  return toMarkdownFilename(artifact.display_name || "artifact");
}

export function downloadMarkdownFile(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
