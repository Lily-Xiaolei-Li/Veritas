/**
 * FileList Component (B1.2)
 *
 * Scrollable list of files with selection support.
 * Note: For very large file counts (500+), virtualization should be added.
 */

"use client";

import React from "react";
import { useTranslations } from "next-intl";
import { FileItem } from "./FileItem";
import { Loader2, FolderOpen, AlertCircle } from "lucide-react";
import type { FileIndex } from "@/lib/api/types";

interface FileListProps {
  files: FileIndex[];
  selectedFileIds: string[];
  onToggleSelect: (fileId: string) => void;
  isLoading?: boolean;
  error?: string | null;
}

export function FileList({
  files,
  selectedFileIds,
  onToggleSelect,
  isLoading,
  error,
}: FileListProps) {
  const t = useTranslations("files");
  // Loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-500">
        <Loader2 className="h-8 w-8 animate-spin mb-2" />
        <span className="text-sm">{t("loading")}</span>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-red-500">
        <AlertCircle className="h-8 w-8 mb-2" />
        <span className="text-sm font-medium">{t("loadFailed")}</span>
        <span className="text-xs text-red-400 mt-1">{error}</span>
      </div>
    );
  }

  // Empty state
  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-500">
        <FolderOpen className="h-12 w-12 mb-2 text-gray-300" />
        <span className="text-sm font-medium">{t("emptyTitle")}</span>
        <span className="text-xs text-gray-400 mt-1">{t("emptyHint")}</span>
      </div>
    );
  }

  // File list
  return (
    <div className="overflow-auto h-full">
      {files.map((file) => (
        <FileItem
          key={file.id}
          file={file}
          isSelected={selectedFileIds.includes(file.id)}
          onToggleSelect={() => onToggleSelect(file.id)}
        />
      ))}
    </div>
  );
}
