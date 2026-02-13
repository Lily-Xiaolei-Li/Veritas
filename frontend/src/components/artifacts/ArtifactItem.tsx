/**
 * ArtifactItem Component (B1.3 - Artifact Handling)
 *
 * Single artifact row in the artifact list.
 * Shows icon, name, type badge, size, and download button.
 */

"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  FileText,
  FileCode,
  Image as ImageIcon,
  File,
  Terminal,
  AlertCircle,
  Pin,
  Pencil,
} from "lucide-react";
import { Badge } from "../ui/Badge";
import { cn } from "@/lib/utils/cn";
import { getArtifactDownloadUrl, useDeleteArtifact } from "@/lib/hooks/useArtifacts";
import type { ArtifactPreviewKind } from "@/lib/api/types";
import { downloadMarkdownFile, getArtifactMarkdownName } from "@/lib/artifacts/download";
import type { ArtifactLike } from "@/lib/artifacts/types";
import { isLocalArtifact } from "@/lib/artifacts/types";
import { useWorkbenchStore } from "@/lib/store";

interface ArtifactItemProps {
  artifact: ArtifactLike;
  isSelected: boolean;
  isFocused?: boolean;
  isEditTarget?: boolean;
  isChecked?: boolean;
  showCheckbox?: boolean;
  onToggleFocus?: () => void;
  onToggleEdit?: () => void;
  onToggleCheck?: () => void;
  onClick: () => void;
}

/**
 * Get icon component based on preview kind and extension.
 */
function getArtifactIcon(artifact: ArtifactLike): React.ReactNode {
  const { preview_kind, artifact_type } = artifact;

  // Special types
  if (artifact_type === "stdout" || artifact_type === "stderr") {
    return <Terminal className="h-4 w-4" />;
  }
  if (artifact_type === "log") {
    return <FileText className="h-4 w-4" />;
  }

  // Based on preview kind
  switch (preview_kind) {
    case "code":
      return <FileCode className="h-4 w-4" />;
    case "image":
      return <ImageIcon className="h-4 w-4" />;
    case "text":
    case "markdown":
      return <FileText className="h-4 w-4" />;
    default:
      return <File className="h-4 w-4" />;
  }
}

/**
 * Get icon color based on preview kind.
 */
function getIconColor(previewKind: ArtifactPreviewKind): string {
  switch (previewKind) {
    case "code":
      return "text-blue-500";
    case "image":
      return "text-purple-500";
    case "text":
      return "text-gray-500";
    case "markdown":
      return "text-green-500";
    default:
      return "text-gray-400";
  }
}

/**
 * Format file size for display.
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

/**
 * Format relative date for display.
 */
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

/**
 * Get type badge variant.
 */
function getTypeBadgeVariant(
  artifactType: string
): "default" | "success" | "warning" | "error" | "info" {
  switch (artifactType) {
    case "stdout":
      return "success";
    case "stderr":
      return "error";
    case "log":
      return "warning";
    default:
      return "default";
  }
}

export function ArtifactItem({
  artifact,
  isSelected,
  isFocused = false,
  isEditTarget = false,
  isChecked = false,
  showCheckbox = false,
  onToggleFocus,
  onToggleEdit,
  onToggleCheck,
  onClick,
}: ArtifactItemProps) {
  const isLocal = isLocalArtifact(artifact);
  const downloadUrl = isLocal ? "" : getArtifactDownloadUrl(artifact.id);

  const { mutateAsync: deleteRemoteArtifact, isPending: isDeletingRemote } = useDeleteArtifact();
  const removeLocalArtifact = useWorkbenchStore((s) => s.removeLocalArtifact);
  const removeArtifactEdit = useWorkbenchStore((s) => s.removeArtifactEdit);

  const [showContextMenu, setShowContextMenu] = useState(false);
  const [contextMenuPos, setContextMenuPos] = useState({ x: 0, y: 0 });
  const [showRenameModal, setShowRenameModal] = useState(false);
  const [newName, setNewName] = useState(artifact.display_name);
  const [isRenaming, setIsRenaming] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close context menu on click outside
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && e.target instanceof Node && menuRef.current.contains(e.target)) {
        return;
      }
      setShowContextMenu(false);
    };
    if (showContextMenu) {
      document.addEventListener("click", handleClick);
      return () => document.removeEventListener("click", handleClick);
    }
  }, [showContextMenu]);

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenuPos({ x: e.clientX, y: e.clientY });
    setShowContextMenu(true);
  };

  const handleDownload = () => {
    if (isLocal) {
      downloadMarkdownFile(getArtifactMarkdownName(artifact), artifact.content);
      return;
    }
    window.open(downloadUrl, "_blank");
  };

  const handleDelete = async () => {
    const ok = window.confirm(`Delete artifact "${artifact.display_name}"?`);
    if (!ok) return;

    try {
      if (isLocal) {
        removeLocalArtifact(artifact.id);
        removeArtifactEdit(artifact.id);
        return;
      }
      await deleteRemoteArtifact(artifact.id);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      alert(message);
    }
  };

  const handleRename = async () => {
    if (!newName.trim() || newName === artifact.display_name) {
      setShowRenameModal(false);
      return;
    }

    setIsRenaming(true);
    try {
      const res = await fetch(`http://localhost:8001/api/v1/artifacts/${artifact.id}/rename`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: newName.trim() }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }

      // Refresh the artifacts list
      window.location.reload();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      alert(`Failed to rename: ${message}`);
    } finally {
      setIsRenaming(false);
      setShowRenameModal(false);
    }
  };

  return (
    <>
      <div
        className={cn(
          "flex items-center gap-3 px-3 py-2 border-b border-gray-100",
          "hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer transition-colors",
          isSelected &&
            "bg-blue-50 dark:bg-gray-800 hover:bg-blue-100 dark:hover:bg-gray-800"
        )}
        onClick={onClick}
        onContextMenu={handleContextMenu}
      >
      {/* Checkbox for batch selection */}
      {showCheckbox && (
        <input
          type="checkbox"
          className="h-3.5 w-3.5 flex-shrink-0 accent-purple-600"
          checked={isChecked}
          onChange={(e) => {
            e.stopPropagation();
            onToggleCheck?.();
          }}
          onClick={(e) => e.stopPropagation()}
        />
      )}

      {/* Icon */}
      <div className={cn("flex-shrink-0", getIconColor(artifact.preview_kind))}>
        {getArtifactIcon(artifact)}
      </div>

      {/* Name and metadata */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
            {artifact.display_name}
          </span>
          {artifact.artifact_type !== "file" && (
            <Badge
              variant={getTypeBadgeVariant(artifact.artifact_type)}
              size="sm"
            >
              {artifact.artifact_type}
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
          <span>{formatFileSize(artifact.size_bytes)}</span>
          <span>-</span>
          <span>{formatDate(artifact.created_at)}</span>
          {!artifact.can_preview && (
            <>
              <span>-</span>
              <span className="flex items-center gap-1 text-amber-600">
                <AlertCircle className="h-3 w-3" />
                No preview
              </span>
            </>
          )}
        </div>
      </div>

      {/* Edit target button */}
      {onToggleEdit && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onToggleEdit();
          }}
          className={cn(
            "flex-shrink-0 p-1.5 rounded",
            isEditTarget
              ? "text-amber-700 bg-amber-50 hover:bg-amber-100 dark:text-amber-400 dark:bg-amber-900/30 dark:hover:bg-amber-900/50"
              : "text-gray-400 hover:text-amber-700 hover:bg-amber-50 dark:hover:text-amber-400 dark:hover:bg-amber-900/30",
            "transition-colors"
          )}
          title={isEditTarget ? "Cancel edit target" : "Set as edit target (AI will update this)"}
          aria-label={isEditTarget ? "Cancel edit target" : "Set as edit target"}
        >
          <Pencil className="h-4 w-4" />
        </button>
      )}

      {/* Focus (pin) button */}
      {onToggleFocus && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onToggleFocus();
          }}
          className={cn(
            "flex-shrink-0 p-1.5 rounded",
            isFocused
              ? "text-purple-700 bg-purple-50 hover:bg-purple-100 dark:text-purple-400 dark:bg-purple-900/30 dark:hover:bg-purple-900/50"
              : "text-gray-400 hover:text-purple-700 hover:bg-purple-50 dark:hover:text-purple-400 dark:hover:bg-purple-900/30",
            "transition-colors"
          )}
          title={isFocused ? "Unfocus" : "Focus (pin) for chat context"}
          aria-label={isFocused ? "Unfocus artifact" : "Focus artifact"}
        >
          <Pin className="h-4 w-4" />
        </button>
      )}

    </div>

      {/* Context menu (right-click) */}
      {showContextMenu && (
        <div
          ref={menuRef}
          className={cn(
            "fixed bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700",
            "rounded-md shadow-lg py-1 z-50 min-w-[160px]"
          )}
          style={{ left: contextMenuPos.x, top: contextMenuPos.y }}
        >
          {!isLocal && (
            <button
              className="w-full px-4 py-1.5 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-900 dark:text-gray-100"
              onClick={() => {
                setShowContextMenu(false);
                setNewName(artifact.display_name);
                setShowRenameModal(true);
              }}
            >
              Rename
            </button>
          )}
          <button
            className="w-full px-4 py-1.5 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-900 dark:text-gray-100"
            onClick={() => {
              setShowContextMenu(false);
              handleDownload();
            }}
          >
            Download
          </button>
          {!isLocal && (
            <button
              className="w-full px-4 py-1.5 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-900 dark:text-gray-100"
              onClick={async () => {
                setShowContextMenu(false);
                try {
                  const res = await fetch(`http://localhost:8001/api/v1/artifacts/${artifact.id}/copy`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                  });
                  if (!res.ok) {
                    const text = await res.text();
                    throw new Error(text || `HTTP ${res.status}`);
                  }
                  // Refresh artifacts list
                  window.location.reload();
                } catch (err) {
                  const message = err instanceof Error ? err.message : String(err);
                  alert(`Failed to copy: ${message}`);
                }
              }}
            >
              Copy
            </button>
          )}
          <button
            className={cn(
              "w-full px-4 py-1.5 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-800",
              "text-red-600",
              isDeletingRemote && !isLocal && "opacity-50 cursor-not-allowed"
            )}
            disabled={isDeletingRemote && !isLocal}
            onClick={(e) => {
              e.stopPropagation();
              setShowContextMenu(false);
              // Use setTimeout to ensure menu closes before confirm dialog
              setTimeout(() => {
                void handleDelete();
              }, 50);
            }}
          >
            Delete
          </button>
        </div>
      )}

      {/* Rename modal */}
      {showRenameModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowRenameModal(false)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-sm mx-4 p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              Rename Artifact
            </h3>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleRename();
                if (e.key === 'Escape') setShowRenameModal(false);
              }}
            />
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => setShowRenameModal(false)}
                className="px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
              >
                Cancel
              </button>
              <button
                onClick={handleRename}
                disabled={!newName.trim() || isRenaming}
                className={cn(
                  "px-4 py-2 text-sm text-white rounded-md",
                  "bg-blue-500 hover:bg-blue-600",
                  "disabled:bg-blue-300 disabled:cursor-not-allowed"
                )}
              >
                {isRenaming ? "Renaming..." : "Rename"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
