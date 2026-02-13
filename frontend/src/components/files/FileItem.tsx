/**
 * FileItem Component (B1.2)
 *
 * Single file row in the file browser list.
 */

"use client";

import React from "react";
import {
  File,
  FileCode,
  FileImage,
  FileText,
  FileJson,
} from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { FileIndex } from "@/lib/api/types";

interface FileItemProps {
  file: FileIndex;
  isSelected: boolean;
  onToggleSelect: () => void;
}

/**
 * Get icon component based on file extension.
 */
function getFileIcon(extension: string | null) {
  switch (extension?.toLowerCase()) {
    case "ts":
    case "tsx":
    case "js":
    case "jsx":
    case "py":
    case "rs":
    case "go":
    case "java":
    case "cpp":
    case "c":
    case "h":
      return FileCode;
    case "png":
    case "jpg":
    case "jpeg":
    case "gif":
    case "svg":
    case "webp":
      return FileImage;
    case "md":
    case "txt":
    case "log":
      return FileText;
    case "json":
    case "yaml":
    case "yml":
    case "toml":
      return FileJson;
    default:
      return File;
  }
}

/**
 * Get color class based on file extension.
 */
function getIconColor(extension: string | null): string {
  switch (extension?.toLowerCase()) {
    case "ts":
    case "tsx":
      return "text-blue-500";
    case "js":
    case "jsx":
      return "text-yellow-500";
    case "py":
      return "text-green-500";
    case "json":
      return "text-orange-500";
    case "md":
      return "text-gray-600";
    default:
      return "text-gray-400";
  }
}

/**
 * Format file size to human readable string.
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";

  const units = ["B", "KB", "MB", "GB"];
  const k = 1024;
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${units[i]}`;
}

/**
 * Format date to relative or absolute string.
 */
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

export function FileItem({ file, isSelected, onToggleSelect }: FileItemProps) {
  const Icon = getFileIcon(file.extension);
  const iconColor = getIconColor(file.extension);

  return (
    <div
      className={cn(
        "flex items-center gap-3 px-3 py-2 border-b border-gray-100 cursor-pointer transition-colors",
        "hover:bg-gray-50",
        isSelected && "bg-blue-50 hover:bg-blue-100"
      )}
      onClick={onToggleSelect}
    >
      {/* Checkbox */}
      <div className="flex-shrink-0">
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleSelect}
          onClick={(e) => e.stopPropagation()}
          className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
        />
      </div>

      {/* Icon */}
      <div className="flex-shrink-0">
        <Icon className={cn("h-5 w-5", iconColor)} />
      </div>

      {/* Filename and path */}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm text-gray-900 truncate">
          {file.filename}
        </div>
        {file.parent_dir && (
          <div className="text-xs text-gray-500 truncate">{file.parent_dir}</div>
        )}
      </div>

      {/* Size */}
      <div className="flex-shrink-0 text-xs text-gray-500 w-16 text-right">
        {formatFileSize(file.size_bytes)}
      </div>

      {/* Modified date */}
      <div className="flex-shrink-0 text-xs text-gray-500 w-20 text-right">
        {formatDate(file.modified_at)}
      </div>
    </div>
  );
}
