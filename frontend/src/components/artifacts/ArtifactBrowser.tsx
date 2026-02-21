/**
 * ArtifactBrowser Component (B1.3 - Artifact Handling)
 *
 * Main container for artifact browsing with list and preview split view.
 */

"use client";

import React, { useMemo, useRef, useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
  type ImperativePanelHandle,
} from "react-resizable-panels";
import {
  RefreshCw,
  Download,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  ChevronDown,
  Plus,
  FilePlus,
  CheckSquare,
  Pin,
  Trash2,
  Layers,
} from "lucide-react";
import { Button } from "../ui/Button";
import { ArtifactList } from "./ArtifactList";
import { ArtifactPreview } from "./ArtifactPreview";
import { useSessionArtifacts, useDeleteArtifact, getRunZipDownloadUrl } from "@/lib/hooks/useArtifacts";
import { useWorkbenchStore } from "@/lib/store";
import { cn } from "@/lib/utils/cn";
import type { ArtifactListParams } from "@/lib/api/types";
import { isLocalArtifact } from "@/lib/artifacts/types";
import { uploadDocument } from "@/lib/api/documents";
import { API_BASE_URL } from "@/lib/utils/constants";

interface ArtifactBrowserProps {
  knowledgeSourcesSlot?: React.ReactNode;
}

export function ArtifactBrowser({ knowledgeSourcesSlot }: ArtifactBrowserProps) {
  const t = useTranslations("artifacts");
  const currentSessionId = useWorkbenchStore((s) => s.currentSessionId);
  const selectedArtifactId = useWorkbenchStore((s) => s.selectedArtifactId);
  const focusedArtifactIds = useWorkbenchStore((s) => s.focusedArtifactIds);
  const checkedArtifactIds = useWorkbenchStore((s) => s.checkedArtifactIds);
  const textSelections = useWorkbenchStore((s) => s.textSelections);
  const editTargetArtifactId = useWorkbenchStore((s) => s.editTargetArtifactId);
  const editTargetSelections = useWorkbenchStore((s) => s.editTargetSelections);
  const toggleFocusedArtifact = useWorkbenchStore((s) => s.toggleFocusedArtifact);
  const toggleEditTarget = useWorkbenchStore((s) => s.toggleEditTarget);
  const clearFocusedArtifacts = useWorkbenchStore((s) => s.clearFocusedArtifacts);
  const clearTextSelections = useWorkbenchStore((s) => s.clearTextSelections);
  const setEditTarget = useWorkbenchStore((s) => s.setEditTarget);
  const clearEditTargetSelections = useWorkbenchStore((s) => s.clearEditTargetSelections);
  const toggleCheckedArtifact = useWorkbenchStore((s) => s.toggleCheckedArtifact);
  const setCheckedArtifacts = useWorkbenchStore((s) => s.setCheckedArtifacts);
  const clearCheckedArtifacts = useWorkbenchStore((s) => s.clearCheckedArtifacts);
  const focusCheckedArtifacts = useWorkbenchStore((s) => s.focusCheckedArtifacts);
  const focusMode = useWorkbenchStore((s) => s.focusMode);
  const setFocusMode = useWorkbenchStore((s) => s.setFocusMode);
  const artifactScope = useWorkbenchStore((s) => s.artifactScope);
  const setArtifactScope = useWorkbenchStore((s) => s.setArtifactScope);

  const setSelectedArtifact = useWorkbenchStore((s) => s.setSelectedArtifact);
  const localArtifacts = useWorkbenchStore((s) => s.localArtifacts);

  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isToolbarCollapsed, setIsToolbarCollapsed] = useState(false);
  const [batchSelectMode, setBatchSelectMode] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isMerging, setIsMerging] = useState(false);
  
  // New artifact modal state
  const [showNewModal, setShowNewModal] = useState(false);
  const [newArtifactName, setNewArtifactName] = useState("");
  const [creatingNew, setCreatingNew] = useState(false);
  
  // Editor maximize state
  const isEditorMaximized = useWorkbenchStore((s) => s.isEditorMaximized);

  // Delete mutation
  const deleteMutation = useDeleteArtifact();

  // Collapsible artifact list panel
  const listPanelRef = useRef<ImperativePanelHandle>(null);
  const [isListCollapsed, setIsListCollapsed] = useState(false);

  // Respond to editor maximize state
  useEffect(() => {
    if (isEditorMaximized) {
      setIsToolbarCollapsed(true);
      listPanelRef.current?.collapse();
      setIsListCollapsed(true);
    } else {
      setIsToolbarCollapsed(false);
      listPanelRef.current?.expand(30);
      setIsListCollapsed(false);
    }
  }, [isEditorMaximized]);

  // Query params
  const [params, setParams] = useState<ArtifactListParams>({
    limit: 50,
    offset: 0,
    sort: "created_desc",
  });

  // Fetch artifacts
  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useSessionArtifacts(currentSessionId, params);

  const artifacts = useMemo(() => data?.artifacts ?? [], [data?.artifacts]);
  const total = data?.total || 0;
  const hasMore = data?.has_more || false;

  const visibleLocalArtifacts = useMemo(() => {
    if (!currentSessionId) return localArtifacts;
    return localArtifacts.filter((artifact) => artifact.session_id === currentSessionId);
  }, [localArtifacts, currentSessionId]);

  const combinedArtifacts = useMemo(() => {
    const merged = [...visibleLocalArtifacts, ...artifacts];
    const sort = params.sort || "created_desc";
    return merged.sort((a, b) => {
      switch (sort) {
        case "name_asc":
          return a.display_name.localeCompare(b.display_name);
        case "size_desc":
          return (b.size_bytes || 0) - (a.size_bytes || 0);
        case "created_desc":
        default:
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });
  }, [visibleLocalArtifacts, artifacts, params.sort]);

  // Find selected artifact
  const selectedArtifact =
    combinedArtifacts.find((a) => a.id === selectedArtifactId) || null;

  // Get unique run IDs for ZIP download
  const runIds = [
    ...new Set(artifacts.filter((a) => !isLocalArtifact(a)).map((a) => a.run_id)),
  ];

  // Handlers
  const handleRefresh = () => {
    refetch();
  };

  const handlePrevPage = () => {
    if (params.offset && params.offset > 0) {
      setParams((p) => ({
        ...p,
        offset: Math.max(0, (p.offset || 0) - (p.limit || 50)),
      }));
    }
  };

  const handleNextPage = () => {
    if (hasMore) {
      setParams((p) => ({
        ...p,
        offset: (p.offset || 0) + (p.limit || 50),
      }));
    }
  };

  const handleSortChange = (sort: ArtifactListParams["sort"]) => {
    setParams((p) => ({ ...p, sort, offset: 0 }));
  };

  const handleUploadClick = () => {
    if (!currentSessionId) {
      setUploadError("No session selected");
      return;
    }
    setUploadError(null);
    fileInputRef.current?.click();
  };

  const handleFileSelected = async (file: File | null) => {
    if (!file) return;
    if (!currentSessionId) {
      setUploadError("No session selected");
      return;
    }

    setUploading(true);
    setUploadError(null);
    try {
      const result = await uploadDocument({ sessionId: currentSessionId, file });

      // refresh artifacts panel
      queryClient.invalidateQueries({ queryKey: ["session-artifacts", currentSessionId] });
      queryClient.invalidateQueries({ queryKey: ["run-artifacts"] });

      const first = result.artifacts?.[0]?.artifact_id;
      if (first) setSelectedArtifact(first);

      if (!result.success) {
        const msg = (result.errors && result.errors[0]) || "Upload finished with errors";
        setUploadError(msg);
      }
    } catch (e) {
      setUploadError((e as Error).message || "Upload failed");
    } finally {
      setUploading(false);
      // allow selecting same file again
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDownloadAll = () => {
    // Download ZIP for first run (or could show a selector)
    if (runIds.length > 0) {
      const url = getRunZipDownloadUrl(runIds[0]);
      window.open(url, "_blank");
    }
  };

  // Handler for creating a new blank artifact
  const handleCreateNew = async () => {
    if (!currentSessionId || !newArtifactName.trim()) return;
    
    setCreatingNew(true);
    setUploadError(null);
    try {
      const filename = newArtifactName.trim().endsWith('.md') 
        ? newArtifactName.trim() 
        : `${newArtifactName.trim()}.md`;
      
      const res = await fetch(`${API_BASE_URL}/api/v1/sessions/${currentSessionId}/artifacts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename,
          content: `# ${newArtifactName.trim().replace(/\.md$/, '')}\n\n`,
          artifact_type: 'file',
        }),
      });
      
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      
      const data = await res.json();
      
      // Refresh artifacts
      queryClient.invalidateQueries({ queryKey: ["session-artifacts", currentSessionId] });
      queryClient.invalidateQueries({ queryKey: ["run-artifacts"] });
      
      // Select the new artifact
      if (data.id) {
        setSelectedArtifact(data.id);
      }
      
      // Close modal and reset
      setShowNewModal(false);
      setNewArtifactName("");
    } catch (e) {
      setUploadError((e as Error).message || "Failed to create artifact");
    } finally {
      setCreatingNew(false);
    }
  };

  const handleDeleteSelected = async () => {
    if (checkedArtifactIds.length === 0) return;
    
    // Filter out local artifacts (they can't be deleted via API)
    const deletableIds = checkedArtifactIds.filter(
      (id) => !combinedArtifacts.find((a) => a.id === id && isLocalArtifact(a))
    );
    
    if (deletableIds.length === 0) {
      // All selected are local artifacts
      clearCheckedArtifacts();
      return;
    }

    setIsDeleting(true);
    try {
      // Delete all selected artifacts in parallel
      await Promise.all(deletableIds.map((id) => deleteMutation.mutateAsync(id)));
      clearCheckedArtifacts();
      // If currently selected artifact was deleted, clear selection
      if (selectedArtifactId && deletableIds.includes(selectedArtifactId)) {
        setSelectedArtifact(null);
      }
    } catch (e) {
      console.error("Failed to delete artifacts:", e);
    } finally {
      setIsDeleting(false);
    }
  };

  // Merge selected artifacts by time sequence
  const handleMergeSelected = async () => {
    if (checkedArtifactIds.length < 2 || !currentSessionId) return;
    
    setIsMerging(true);
    try {
      // Get all selected artifacts and sort by creation time
      const selectedArtifacts = combinedArtifacts
        .filter((a) => checkedArtifactIds.includes(a.id))
        .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
      
      // Fetch content for each artifact
      const contents: string[] = [];
      for (const artifact of selectedArtifacts) {
        let content = "";
        if (isLocalArtifact(artifact) && artifact.content) {
          content = artifact.content;
        } else {
          // Fetch from backend
          const res = await fetch(`${API_BASE_URL}/api/v1/artifacts/${artifact.id}/preview`);
          if (res.ok) {
            const preview = await res.json();
            content = preview.text || preview.content || "";
          }
        }
        if (content) {
          contents.push(`## ${artifact.display_name}\n\n${content}`);
        }
      }
      
      if (contents.length === 0) {
        throw new Error("No content to merge");
      }
      
      // Create merged content
      const mergedContent = contents.join("\n\n---\n\n");
      const timestamp = new Date().toISOString().split("T")[0];
      const mergedName = `merged_${timestamp}_${selectedArtifacts.length}files.md`;
      
      // Save as new artifact
      const res = await fetch(`${API_BASE_URL}/api/v1/sessions/${currentSessionId}/artifacts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: mergedName,
          content: mergedContent,
          artifact_meta: {
            merged_from: selectedArtifacts.map((a) => a.id),
            merge_count: selectedArtifacts.length,
          },
        }),
      });
      
      if (!res.ok) {
        throw new Error("Failed to create merged artifact");
      }
      
      const newArtifact = await res.json();
      
      // Refresh artifacts list
      queryClient.invalidateQueries({ queryKey: ["session-artifacts", currentSessionId] });
      
      // Select the new merged artifact
      setSelectedArtifact(newArtifact.id);
      
      // Clear selection
      clearCheckedArtifacts();
      
      // Trigger flash effect
      const { setArtifactFlash } = useWorkbenchStore.getState();
      setArtifactFlash(newArtifact.id);
      
    } catch (e) {
      console.error("Failed to merge artifacts:", e);
    } finally {
      setIsMerging(false);
    }
  };

  // Pagination info
  const start = (params.offset || 0) + 1;
  const end = Math.min((params.offset || 0) + artifacts.length, total);
  const canPrev = (params.offset || 0) > 0;
  const canNext = hasMore;
  const localCount = visibleLocalArtifacts.length;

  return (
    <div className="flex flex-col h-full">
      {/* Unified Toolbar - all controls in one row */}
      {isToolbarCollapsed ? (
        <button
          onClick={() => setIsToolbarCollapsed(false)}
          className="flex items-center justify-center gap-1.5 w-full px-3 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        >
          <ChevronDown className="h-5 w-5 text-gray-700 dark:text-gray-200" />
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-200 tracking-wide uppercase">{t("resources")}</span>
        </button>
      ) : (
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        {/* Left group - Knowledge sources */}
        <div className="flex items-center gap-1.5">
          {knowledgeSourcesSlot}
        </div>

        {/* Divider */}
        {knowledgeSourcesSlot && (
          <div className="h-4 w-px bg-gray-300 dark:bg-gray-600" />
        )}

        {/* Middle group - Artifact controls */}
        <div className="flex items-center gap-1.5">
          {/* Hidden file input for document upload */}
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".docx,.xlsx,.xls,.csv,.pdf,.txt,.md,.json"
            onChange={(e) => handleFileSelected(e.target.files?.[0] || null)}
          />

          {/* New blank artifact */}
          <button
            onClick={() => setShowNewModal(true)}
            disabled={!currentSessionId}
            className={cn(
              "flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded transition-colors",
              "bg-blue-500 text-white hover:bg-blue-600",
              "disabled:bg-blue-300 disabled:cursor-not-allowed"
            )}
            title={!currentSessionId ? "Select a session first" : "Create new blank artifact"}
          >
            <FilePlus className="h-3 w-3" />
            <span>{t("new")}</span>
          </button>

          {/* Upload document */}
          <button
            onClick={handleUploadClick}
            disabled={!currentSessionId || uploading}
            className={cn(
              "flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded transition-colors",
              "bg-blue-500 text-white hover:bg-blue-600",
              "disabled:bg-blue-300 disabled:cursor-not-allowed"
            )}
            title={
              !currentSessionId
                ? "Select a session first"
                : uploading
                ? "Uploading..."
                : "Import document file"
            }
          >
            <Plus className="h-3 w-3" />
            <span>{uploading ? "..." : t("import")}</span>
          </button>

          <select
            value={params.sort || "created_desc"}
            onChange={(e) =>
              handleSortChange(e.target.value as ArtifactListParams["sort"])
            }
            className="text-[11px] border border-gray-300 dark:border-gray-600 rounded px-1.5 py-0.5 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            title={t("sortOrder")}
          >
            <option value="created_desc">{t("sort.newestFirst")}</option>
            <option value="name_asc">{t("sort.nameAZ")}</option>
            <option value="size_desc">{t("sort.largestFirst")}</option>
          </select>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={isFetching}
            title={t("refresh")}
            className="p-1"
          >
            <RefreshCw className={cn("h-3 w-3", isFetching && "animate-spin")} />
          </Button>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Right group - Context controls & pagination */}
        <div className="flex items-center gap-1.5">
          <select
            value={artifactScope}
            onChange={(e) => setArtifactScope(e.target.value as "session" | "all_sessions")}
            className="text-[11px] border border-gray-300 dark:border-gray-600 rounded px-1.5 py-0.5 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            title={t("scopeTitle")}
          >
            <option value="session">{t("scope.thisSession")}</option>
            <option value="all_sessions">{t("scope.allSessions")}</option>
          </select>

          <select
            value={focusMode}
            onChange={(e) => setFocusMode(e.target.value as "prefer" | "only")}
            className="text-[11px] border border-gray-300 dark:border-gray-600 rounded px-1.5 py-0.5 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            title={t("focusModeTitle")}
          >
            <option value="prefer">{t("focusMode.prefer")}</option>
            <option value="only">{t("focusMode.only")}</option>
          </select>

          {/* Edit target indicator */}
          {editTargetArtifactId && (
            <div
              className="flex items-center gap-1.5 px-1.5 py-0.5 rounded border border-amber-200 dark:border-amber-400/30 bg-amber-50 dark:bg-amber-900/20"
              title={editTargetSelections.length > 0 
                ? `AI will update ${editTargetSelections.length} selection(s) in this artifact` 
                : "AI will update this entire artifact"}
            >
              <span className="text-[11px] font-medium text-amber-800 dark:text-amber-200">
                ✏️ Edit{editTargetSelections.length > 0 ? ` (${editTargetSelections.length} 📍)` : " mode"}
              </span>
              <button
                className="text-amber-700 hover:text-amber-900 dark:text-amber-200 text-[11px] leading-none"
                onClick={() => {
                  setEditTarget(null);
                  clearEditTargetSelections();
                }}
                title={t("cancelEditTarget")}
                type="button"
              >
                ×
              </button>
            </div>
          )}

          {(focusedArtifactIds.length > 0 || textSelections.length > 0) && (
            <div
              className="flex items-center gap-1.5 px-1.5 py-0.5 rounded border border-purple-200 dark:border-purple-400/30 bg-purple-50 dark:bg-purple-900/20"
              title={`${focusedArtifactIds.length} artifacts, ${textSelections.length} selections`}
            >
              <span className="text-[11px] font-medium text-purple-800 dark:text-purple-200">
                {focusedArtifactIds.length > 0 && `${focusedArtifactIds.length} 📄`}
                {focusedArtifactIds.length > 0 && textSelections.length > 0 && " + "}
                {textSelections.length > 0 && `${textSelections.length} 📌`}
              </span>
              <button
                className="text-purple-700 hover:text-purple-900 dark:text-purple-200 text-[11px] leading-none"
                onClick={() => {
                  clearFocusedArtifacts();
                  clearTextSelections();
                }}
                title={t("clearAllFocused")}
                type="button"
              >
                ×
              </button>
            </div>
          )}

          {(total > 0 || localCount > 0) && (
            <span className="text-[10px] text-gray-500 dark:text-gray-400 tabular-nums">
              {total > 0 ? `${start}-${end} of ${total}` : ""}
              {total > 0 && localCount > 0 ? " · " : ""}
              {localCount > 0 ? `${localCount} local` : ""}
            </span>
          )}

          {artifacts.length > 0 && runIds.length === 1 && (
            <button
              onClick={handleDownloadAll}
              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500"
              title={t("downloadAllZip")}
            >
              <Download className="h-3.5 w-3.5" />
            </button>
          )}
          
          {/* Collapse button */}
          <button
            onClick={() => setIsToolbarCollapsed(true)}
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500"
            title={t("collapseToolbar")}
          >
            <ChevronUp className="h-3 w-3" />
          </button>
        </div>
      </div>
      )}

      {uploadError && (
        <div className="px-3 py-2 border-b border-red-200 bg-red-50 text-xs text-red-700">
          {uploadError}
        </div>
      )}

      {/* Main content - resizable split view */}
      <div className="relative flex-1 overflow-hidden">
        <PanelGroup direction="horizontal" className="h-full" autoSaveId="artifact-browser:v1">
        {/* Artifact list (collapsible) */}
        <Panel
          ref={listPanelRef}
          defaultSize={30}
          minSize={15}
          maxSize={60}
          collapsible
          collapsedSize={3}
          onCollapse={() => setIsListCollapsed(true)}
          onExpand={() => setIsListCollapsed(false)}
          className="overflow-hidden"
        >
          {isListCollapsed ? (
            <button
              type="button"
              className={cn(
                "h-full w-full flex flex-col items-center justify-start",
                "bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700",
                "hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              )}
              onClick={() => listPanelRef.current?.expand(30)}
              title={t("expandArtifactList")}
            >
              <div className="pt-3 text-gray-700 dark:text-gray-200">
                <ChevronRight className="h-5 w-5" />
              </div>
              <div className="mt-3 text-xs font-semibold text-gray-700 dark:text-gray-200 [writing-mode:vertical-rl] rotate-180 tracking-wide">
                Artifacts
              </div>
            </button>
          ) : (
            <div className="h-full border-r border-gray-200 dark:border-gray-700 overflow-hidden flex flex-col bg-white dark:bg-gray-900">
              <div className="flex items-center justify-between px-2 py-1 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
                <span className="text-[11px] font-semibold tracking-wide text-gray-600 dark:text-gray-300 uppercase">
                  Artifacts
                </span>
                <div className="flex items-center gap-0.5">
                  {/* Toggle batch select mode */}
                  <button
                    type="button"
                    className={cn(
                      "p-1 rounded transition-colors",
                      batchSelectMode
                        ? "bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400"
                        : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800"
                    )}
                    onClick={() => {
                      setBatchSelectMode(!batchSelectMode);
                      if (batchSelectMode) clearCheckedArtifacts();
                    }}
                    title={batchSelectMode ? "Exit batch mode" : "Batch select"}
                  >
                    <CheckSquare className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500"
                    onClick={() => listPanelRef.current?.collapse()}
                    title={t("collapseArtifactList")}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* Batch action bar */}
              {batchSelectMode && (
                <div className="flex items-center gap-1 px-2 py-1.5 border-b border-gray-200 dark:border-gray-700 bg-purple-50 dark:bg-purple-900/20">
                  <button
                    className="text-[10px] px-1.5 py-0.5 rounded bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                    onClick={() => setCheckedArtifacts(combinedArtifacts.map((a) => a.id))}
                    title={t("selectAll")}
                  >
                    {t("all")}
                  </button>
                  <button
                    className="text-[10px] px-1.5 py-0.5 rounded bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                    onClick={() => clearCheckedArtifacts()}
                    title={t("selectNone")}
                  >
                    {t("none")}
                  </button>
                  <div className="flex-1" />
                  <button
                    className={cn(
                      "p-1 rounded transition-colors",
                      checkedArtifactIds.length > 0
                        ? "text-purple-600 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-900/30"
                        : "text-gray-400 cursor-not-allowed"
                    )}
                    disabled={checkedArtifactIds.length === 0}
                    onClick={() => focusCheckedArtifacts()}
                    title={`Pin ${checkedArtifactIds.length} selected`}
                  >
                    <Pin className="h-3.5 w-3.5" />
                  </button>
                  <button
                    className={cn(
                      "p-1 rounded transition-colors",
                      checkedArtifactIds.length >= 2 && !isMerging
                        ? "text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/30"
                        : "text-gray-400 cursor-not-allowed"
                    )}
                    disabled={checkedArtifactIds.length < 2 || isMerging}
                    onClick={handleMergeSelected}
                    title={`Merge ${checkedArtifactIds.length} selected (by time)`}
                  >
                    <Layers className={cn("h-3.5 w-3.5", isMerging && "animate-pulse")} />
                  </button>
                  <button
                    className={cn(
                      "p-1 rounded transition-colors",
                      checkedArtifactIds.length > 0 && !isDeleting
                        ? "text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30"
                        : "text-gray-400 cursor-not-allowed"
                    )}
                    disabled={checkedArtifactIds.length === 0 || isDeleting}
                    onClick={handleDeleteSelected}
                    title={`Delete ${checkedArtifactIds.length} selected`}
                  >
                    <Trash2 className={cn("h-3.5 w-3.5", isDeleting && "animate-pulse")} />
                  </button>
                  {checkedArtifactIds.length > 0 && (
                    <span className="text-[10px] text-purple-600 dark:text-purple-400">
                      {checkedArtifactIds.length}
                    </span>
                  )}
                </div>
              )}

              <div className="flex-1 overflow-y-auto">
                <ArtifactList
                  artifacts={combinedArtifacts}
                  isLoading={isLoading}
                  isError={isError}
                  error={error}
                  selectedArtifactId={selectedArtifactId}
                  focusedArtifactIds={focusedArtifactIds}
                  editTargetArtifactId={editTargetArtifactId}
                  checkedArtifactIds={checkedArtifactIds}
                  showCheckboxes={batchSelectMode}
                  onToggleFocus={toggleFocusedArtifact}
                  onToggleEdit={toggleEditTarget}
                  onToggleCheck={toggleCheckedArtifact}
                  onSelectArtifact={setSelectedArtifact}
                />
              </div>

              {/* Pagination */}
              {total > (params.limit || 50) && (
                <div className="flex items-center justify-center gap-2 px-3 py-2 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handlePrevPage}
                    disabled={!canPrev}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Prev
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleNextPage}
                    disabled={!canNext}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
          )}
        </Panel>

        <PanelResizeHandle className="w-1 bg-gray-200 hover:bg-gray-300 transition-colors" />

        {/* (collapsed affordance is rendered inside the collapsed panel) */}

        {/* Preview pane */}
        <Panel defaultSize={70} minSize={40} className="overflow-hidden">
          <div className="h-full overflow-hidden">
            <ArtifactPreview artifact={selectedArtifact} />
          </div>
        </Panel>
        </PanelGroup>
      </div>

      {/* New Artifact Modal */}
      {showNewModal && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowNewModal(false)}
        >
          <div 
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md mx-4 p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              {t("newArtifact")}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-700 dark:text-gray-300 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={newArtifactName}
                  onChange={(e) => setNewArtifactName(e.target.value)}
                  placeholder={t("namePlaceholder")}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newArtifactName.trim()) {
                      handleCreateNew();
                    }
                  }}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Creates a new Markdown file (.md)
                </p>
              </div>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => {
                    setShowNewModal(false);
                    setNewArtifactName("");
                  }}
                  className="px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreateNew}
                  disabled={!newArtifactName.trim() || creatingNew}
                  className={cn(
                    "px-4 py-2 text-sm text-white rounded-md",
                    "bg-blue-500 hover:bg-blue-600",
                    "disabled:bg-blue-300 disabled:cursor-not-allowed"
                  )}
                >
                  {creatingNew ? "Creating..." : "Create"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
