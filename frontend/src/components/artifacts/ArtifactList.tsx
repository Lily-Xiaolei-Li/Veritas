/**
 * ArtifactList Component (B1.3 - Artifact Handling)
 *
 * Scrollable list of artifacts with loading, empty, and error states.
 */

"use client";

import React from "react";
import { Loader2, AlertCircle, FileText } from "lucide-react";
import { useTranslations } from "next-intl";
import { ArtifactItem } from "./ArtifactItem";
import type { ArtifactLike } from "@/lib/artifacts/types";

interface ArtifactListProps {
  artifacts: ArtifactLike[];
  isLoading: boolean;
  isError: boolean;
  error?: Error | null;
  selectedArtifactId: string | null;
  focusedArtifactIds?: string[];
  editTargetArtifactId?: string | null;
  checkedArtifactIds?: string[];
  showCheckboxes?: boolean;
  onSelectArtifact: (artifactId: string) => void;
  onToggleFocus?: (artifactId: string) => void;
  onToggleEdit?: (artifactId: string) => void;
  onToggleCheck?: (artifactId: string) => void;
}

export function ArtifactList({
  artifacts,
  isLoading,
  isError,
  error,
  selectedArtifactId,
  focusedArtifactIds = [],
  editTargetArtifactId = null,
  checkedArtifactIds = [],
  showCheckboxes = false,
  onSelectArtifact,
  onToggleFocus,
  onToggleEdit,
  onToggleCheck,
}: ArtifactListProps) {
  const t = useTranslations("artifacts");
  // Loading state
  if (isLoading && artifacts.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        <Loader2 className="h-6 w-6 animate-spin mr-2" />
        <span>{t("loading")}</span>
      </div>
    );
  }

  // Error state
  if (isError && artifacts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-red-500">
        <AlertCircle className="h-8 w-8 mb-2" />
        <span className="text-sm font-medium">{t("loadFailed")}</span>
        <span className="text-xs text-gray-500 mt-1">
          {error?.message || "Unknown error"}
        </span>
      </div>
    );
  }

  // Empty state
  if (artifacts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-500">
        <FileText className="h-12 w-12 mb-3 text-gray-300" />
        <span className="text-sm font-medium text-gray-600">
          {t("emptyTitle")}
        </span>
        <span className="text-xs text-gray-400 mt-1">
          {t("emptyHint")}
        </span>
      </div>
    );
  }

  // Artifact list
  return (
    <div className="overflow-y-auto">
      {artifacts.map((artifact) => (
        <ArtifactItem
          key={artifact.id}
          artifact={artifact}
          isSelected={selectedArtifactId === artifact.id}
          isFocused={focusedArtifactIds.includes(artifact.id)}
          isEditTarget={editTargetArtifactId === artifact.id}
          isChecked={checkedArtifactIds.includes(artifact.id)}
          showCheckbox={showCheckboxes}
          onToggleFocus={
            onToggleFocus ? () => onToggleFocus(artifact.id) : undefined
          }
          onToggleEdit={
            onToggleEdit ? () => onToggleEdit(artifact.id) : undefined
          }
          onToggleCheck={
            onToggleCheck ? () => onToggleCheck(artifact.id) : undefined
          }
          onClick={() => onSelectArtifact(artifact.id)}
        />
      ))}
    </div>
  );
}
