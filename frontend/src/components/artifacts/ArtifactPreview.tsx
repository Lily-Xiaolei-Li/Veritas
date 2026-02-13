/**
 * ArtifactPreview Component (B1.3 - Artifact Handling)
 *
 * Preview pane for artifacts showing text, code, markdown, or images.
 * Now supports editing mode for text-based artifacts.
 */

"use client";

import React, { useMemo, useState, useEffect, useRef } from "react";
import Image from "next/image";
import {
  FileText,
  Loader2,
  AlertCircle,
  Pencil,
  Save,
  X,
  Undo2,
  Maximize2,
  Minimize2,
} from "lucide-react";
import Editor from "@monaco-editor/react";
import dynamic from "next/dynamic";

// Lazy load TiptapEditor to avoid SSR issues
const TiptapEditor = dynamic(() => import("./TiptapEditor"), { 
  ssr: false,
  loading: () => <div className="p-4 text-gray-500">Loading editor...</div>
});
import { useArtifactPreview, getArtifactDownloadUrl, useSaveArtifact, useUpdateArtifactContent, useArtifactDraft, useUpdateArtifactDraft } from "@/lib/hooks/useArtifacts";
import { getArtifactMarkdownName } from "@/lib/artifacts/download";
import { useWorkbenchStore } from "@/lib/store";
import { isLocalArtifact, type ArtifactLike } from "@/lib/artifacts/types";
import type { ArtifactPreviewKind } from "@/lib/api/types";
import { Persona, getPersonaById } from "@/components/chat/PersonaSelector";
import { streamXiaoLeiChat } from "@/lib/api/xiaoleiChat";
import { API_BASE_URL } from "@/lib/utils/constants";

interface ArtifactPreviewProps {
  artifact: ArtifactLike | null;
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
 * Count words in text (English words, not characters).
 */
function countWords(text: string): number {
  if (!text || !text.trim()) return 0;
  // Split on whitespace and filter out empty strings
  return text.trim().split(/\s+/).filter(word => word.length > 0).length;
}

function getMonacoLanguage(previewKind: ArtifactPreviewKind | undefined, extension: string | null) {
  if (previewKind === "markdown") return "markdown";
  if (previewKind === "text") return "plaintext";

  if (!extension) return "plaintext";

  switch (extension.toLowerCase()) {
    case "ts":
    case "tsx":
      return "typescript";
    case "js":
    case "jsx":
      return "javascript";
    case "json":
      return "json";
    case "py":
      return "python";
    case "go":
      return "go";
    case "rs":
      return "rust";
    case "java":
      return "java";
    case "c":
      return "c";
    case "cpp":
      return "cpp";
    case "cs":
      return "csharp";
    case "html":
      return "html";
    case "css":
      return "css";
    case "scss":
      return "scss";
    case "yml":
    case "yaml":
      return "yaml";
    case "sh":
    case "bash":
      return "shell";
    case "sql":
      return "sql";
    case "md":
    case "markdown":
      return "markdown";
    default:
      return "plaintext";
  }
}

/**
 * Image preview.
 */
function ImagePreview({ artifact }: { artifact: ArtifactLike }) {
  if (isLocalArtifact(artifact)) {
    return (
      <div className="flex items-center justify-center p-4 text-sm text-gray-500">
        Local image previews are not available.
      </div>
    );
  }

  const downloadUrl = getArtifactDownloadUrl(artifact.id);

  return (
    <div className="flex items-center justify-center p-4">
      <Image
        src={downloadUrl}
        alt={artifact.display_name}
        width={1200}
        height={800}
        className="max-w-full max-h-96 object-contain rounded-md shadow-sm"
      />
    </div>
  );
}

/**
 * No preview available state.
 */
function NoPreview({ artifact }: { artifact: ArtifactLike }) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-gray-500">
      <FileText className="h-16 w-16 mb-4 text-gray-300" />
      <span className="text-sm font-medium text-gray-600">
        Preview not available
      </span>
      <span className="text-xs text-gray-400 mt-1 text-center max-w-xs">
        {artifact.size_bytes > 10 * 1024 * 1024
          ? `File too large to preview (${formatFileSize(artifact.size_bytes)})`
          : "This file type cannot be previewed"}
      </span>
    </div>
  );
}

export function ArtifactPreview({ artifact }: ArtifactPreviewProps) {
  const currentSessionId = useWorkbenchStore((s) => s.currentSessionId);
  const setSelectedArtifact = useWorkbenchStore((s) => s.setSelectedArtifact);
  const isEditorMaximized = useWorkbenchStore((s) => s.isEditorMaximized);
  const toggleEditorMaximized = useWorkbenchStore((s) => s.toggleEditorMaximized);
  const artifactFlashId = useWorkbenchStore((s) => s.artifactFlashId);
  
  // Flash effect when content is appended
  const isFlashing = artifact && artifactFlashId === artifact.id;

  const artifactEdits = useWorkbenchStore((s) => s.artifactEdits);
  const removeLocalArtifact = useWorkbenchStore((s) => s.removeLocalArtifact);
  const removeArtifactEdit = useWorkbenchStore((s) => s.removeArtifactEdit);

  const selectedPersonaId = useWorkbenchStore((s) => s.selectedPersonaId);
  const persona: Persona = useMemo(() => getPersonaById(selectedPersonaId), [selectedPersonaId]);

  // Text selection for contextual editing
  const textSelections = useWorkbenchStore((s) => s.textSelections);
  const toggleTextSelection = useWorkbenchStore((s) => s.toggleTextSelection);

  // Edit target selections (B1.7 - Precise Edit Toggle)
  const editTargetArtifactId = useWorkbenchStore((s) => s.editTargetArtifactId);
  const editTargetSelections = useWorkbenchStore((s) => s.editTargetSelections);
  const toggleEditTargetSelection = useWorkbenchStore((s) => s.toggleEditTargetSelection);
  const setEditTarget = useWorkbenchStore((s) => s.setEditTarget);

  // Hooks must be called unconditionally.
  const isLocal = artifact ? isLocalArtifact(artifact) : false;
  const remoteArtifactId = artifact && !isLocal ? artifact.id : null;

  const saveMutation = useSaveArtifact();
  const updateMutation = useUpdateArtifactContent();
  const draftQuery = useArtifactDraft(remoteArtifactId);
  const draftUpdateMutation = useUpdateArtifactDraft();
  const { data: preview, isLoading, isError, refetch } = useArtifactPreview(remoteArtifactId);

  // Editor ref for decorations
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const editorRef = useRef<any>(null);
  const decorationsRef = useRef<string[]>([]);

  // Editing state
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const isEditingRef = useRef(false);
  const [showPreviewInEdit, setShowPreviewInEdit] = useState(false);
  
  // Keep ref in sync with state (for closures in event handlers)
  useEffect(() => {
    isEditingRef.current = isEditing;
  }, [isEditing]);
  
  // Reset preview toggle when exiting edit mode
  useEffect(() => {
    if (!isEditing) setShowPreviewInEdit(false);
  }, [isEditing]);

  // Phase 5: AI rewrite selection
  const [rewriteOpen, setRewriteOpen] = useState(false);
  const [rewritePrompt, setRewritePrompt] = useState("");
  const [rewriteRunning, setRewriteRunning] = useState(false);
  const [rewriteError, setRewriteError] = useState<string | null>(null);
  const [canUndoRewrite, setCanUndoRewrite] = useState(false);
  
  // Title editing state
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editedTitle, setEditedTitle] = useState("");
  const [isSavingTitle, setIsSavingTitle] = useState(false);
  const titleInputRef = useRef<HTMLInputElement>(null);
  const lastRewriteSnapshotRef = useRef<string | null>(null);
  
  // Word count state
  const [selectedWordCount, setSelectedWordCount] = useState<number | null>(null);
  const pendingSelectionRef = useRef<{
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    range: any;
    selectedText: string;
  } | null>(null);
  
  // Create new artifact from selection state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createArtifactName, setCreateArtifactName] = useState("");
  const [createArtifactContent, setCreateArtifactContent] = useState("");
  const [isCreatingArtifact, setIsCreatingArtifact] = useState(false);

  const previewKind: ArtifactPreviewKind | undefined = !artifact
    ? undefined
    : isLocal
      ? artifact.preview_kind
      : preview?.kind;

  const originalContent = useMemo(() => {
    if (!artifact) return "";
    if (isLocalArtifact(artifact)) {
      return artifactEdits[artifact.id] ?? artifact.content ?? "";
    }
    return preview?.text ?? "";
  }, [artifact, artifactEdits, preview?.text]);

  // Total word count for the current content
  const totalWordCount = useMemo(() => {
    const content = isEditing ? editContent : originalContent;
    return countWords(content);
  }, [isEditing, editContent, originalContent]);

  // Reset editing state when artifact changes
  useEffect(() => {
    setIsEditing(false);
    setEditContent("");
    setCanUndoRewrite(false);
    lastRewriteSnapshotRef.current = null;
    setIsEditingTitle(false);
    setEditedTitle("");
    setSelectedWordCount(null);
  }, [artifact?.id]);

  // Focus title input when editing starts
  useEffect(() => {
    if (isEditingTitle && titleInputRef.current) {
      titleInputRef.current.focus();
      titleInputRef.current.select();
    }
  }, [isEditingTitle]);

  // Handle title rename
  const handleTitleSave = async () => {
    if (!artifact || isLocal) return;
    if (!editedTitle.trim() || editedTitle === artifact.display_name) {
      setIsEditingTitle(false);
      return;
    }

    setIsSavingTitle(true);
    try {
      const res = await fetch(`http://localhost:8001/api/v1/artifacts/${artifact.id}/rename`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: editedTitle.trim() }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }

      // Refresh the page to show updated name
      window.location.reload();
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      alert(`Failed to rename: ${message}`);
    } finally {
      setIsSavingTitle(false);
      setIsEditingTitle(false);
    }
  };

  // Phase 1: Auto-save draft while editing remote artifacts
  useEffect(() => {
    if (!artifact) return;
    if (isLocal) return; // local artifacts are already in-memory
    if (!isEditing) return;

    const id = artifact.id;
    const content = editContent;

    // Skip if no change vs original (avoid unnecessary writes)
    if (content === originalContent) return;

    const t = window.setTimeout(() => {
      draftUpdateMutation.mutate({
        artifactId: id,
        draftContent: content,
        isAutoSave: true,
      });
    }, 2000);

    return () => window.clearTimeout(t);
  }, [artifact, isLocal, isEditing, editContent, originalContent, draftUpdateMutation]);

  // Helper to update editor decorations for text selections
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const updateDecorations = (ed: any, artifactId: string | undefined) => {
    if (!ed || !artifactId) return;

    // Focus selections (purple)
    const focusSelectionsForArtifact = textSelections.filter((s) => s.artifactId === artifactId);
    const focusDecorations = focusSelectionsForArtifact.map((sel) => ({
      range: {
        startLineNumber: sel.startLine,
        startColumn: 1,
        endLineNumber: sel.endLine,
        endColumn: 1000,
      },
      options: {
        isWholeLine: true,
        className: "text-selection-highlight",
        glyphMarginClassName: "text-selection-glyph",
        overviewRuler: {
          color: "#6366f1", // Purple
          position: 4,
        },
      },
    }));

    // Edit target selections (amber/orange) - only if this artifact is the edit target
    const editSelectionsForArtifact = editTargetArtifactId === artifactId
      ? editTargetSelections.filter((s) => s.artifactId === artifactId)
      : [];
    const editDecorations = editSelectionsForArtifact.map((sel) => ({
      range: {
        startLineNumber: sel.startLine,
        startColumn: 1,
        endLineNumber: sel.endLine,
        endColumn: 1000,
      },
      options: {
        isWholeLine: true,
        className: "edit-selection-highlight",
        glyphMarginClassName: "edit-selection-glyph",
        overviewRuler: {
          color: "#f59e0b", // Amber
          position: 4,
        },
      },
    }));

    const allDecorations = [...focusDecorations, ...editDecorations];
    decorationsRef.current = ed.deltaDecorations(decorationsRef.current, allDecorations);
  };

  // Update decorations when selections change
  useEffect(() => {
    if (editorRef.current && artifact) {
      updateDecorations(editorRef.current, artifact.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [textSelections, editTargetSelections, editTargetArtifactId, artifact?.id]);

  // Auto-refetch when flash is triggered (must be before early return)
  useEffect(() => {
    if (isFlashing && !isLocal) {
      void refetch();
    }
  }, [isFlashing, isLocal, refetch]);

  // No artifact selected
  if (!artifact) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-500 p-8">
        <FileText className="h-12 w-12 mb-3 text-gray-300" />
        <span className="text-sm text-gray-600">Select an artifact to preview</span>
      </div>
    );
  }

  const canShowEditor =
    previewKind === "code" || previewKind === "markdown" || previewKind === "text";

  const editorLanguage = getMonacoLanguage(previewKind, artifact.extension);
  const truncated = !isLocal && !!preview?.truncated;
  
  // Content to display: edit buffer when editing, original otherwise
  const displayContent = isEditing ? editContent : originalContent;
  const hasChanges = isEditing && editContent !== originalContent;

  const handleStartEdit = async () => {
    // If remote artifact has a saved draft, restore it to prevent data loss.
    if (!isLocal && remoteArtifactId) {
      try {
        const res = await draftQuery.refetch();
        const draft = res.data;
        if (draft?.is_draft && typeof draft.draft_content === "string") {
          setEditContent(draft.draft_content);
          setIsEditing(true);
          return;
        }
      } catch {
        // ignore: fall back to original content
      }
    }

    setEditContent(originalContent);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditContent("");
  };

  const handleSave = async () => {
    if (!artifact || !currentSessionId) return;

    try {
      if (isLocal) {
        // Save local artifact as new DB artifact
        const filename = getArtifactMarkdownName(artifact);
        const saved = await saveMutation.mutateAsync({
          sessionId: currentSessionId,
          filename,
          content: editContent,
          sourceArtifactId: undefined,
          artifactMeta: {
            saved_from: "local_edit",
            original_display_name: artifact.display_name,
          },
        });

        removeLocalArtifact(artifact.id);
        removeArtifactEdit(artifact.id);
        setSelectedArtifact(saved.id);
      } else {
        // Update existing remote artifact
        await updateMutation.mutateAsync({
          artifactId: artifact.id,
          content: editContent,
        });

        // Clear server-side draft after a successful explicit save
        try {
          await draftUpdateMutation.mutateAsync({
            artifactId: artifact.id,
            draftContent: "",
            isAutoSave: false,
            clear: true,
          });
        } catch {
          // ignore
        }
        
        // Refetch preview to get updated content
        await refetch();
      }

      setIsEditing(false);
      setEditContent("");
    } catch (e) {
      console.error(e);
    }
  };

  const isSaving = saveMutation.isPending || updateMutation.isPending;

  const handleUndoRewrite = () => {
    const editor = editorRef.current;
    if (!editor) return;

    const snapshot = lastRewriteSnapshotRef.current;
    if (!snapshot) return;

    try {
      // Deterministic undo: restore the full document snapshot captured right before the last rewrite.
      // This avoids accidentally undoing unrelated user edits depending on Monaco's internal undo stack.
      editor.setValue(snapshot);
      setEditContent(snapshot);
      lastRewriteSnapshotRef.current = null;
      setCanUndoRewrite(false);
    } catch {
      // ignore
    }
  };

  const runRewrite = async (instruction: string) => {
    if (!isEditing) return;
    
    const sel = pendingSelectionRef.current;
    if (!sel?.selectedText) return;
    
    // For Monaco: use editor and model
    const editor = editorRef.current;
    const model = editor?.getModel?.();
    const hasMonacoRange = sel.range && model;

    setRewriteRunning(true);
    setRewriteError(null);

    const controller = new AbortController();

    const rewriteSystem =
      `${persona.system_prompt}\n\n` +
      "You are editing a document inside an editor. You will be given a selected passage and an instruction. " +
      "Return ONLY the rewritten replacement text for that selected passage. " +
      "Do not add explanations, headings, quotes, code fences, or surrounding context.";

    const userMsg =
      `INSTRUCTION:\n${instruction.trim()}\n\n` +
      `SELECTED_TEXT:\n${sel.selectedText}`;

    let out = "";

    try {
      await streamXiaoLeiChat(
        {
          message: userMsg,
          system_prompt: rewriteSystem,
        },
        {
          signal: controller.signal,
          onToken: (t) => {
            out += t;
          },
          onDone: () => {
            // no-op
          },
          onError: (m) => {
            throw new Error(m || "Rewrite failed");
          },
        }
      );

      const replacement = out.replace(/\s+$/, "");
      if (!replacement) throw new Error("No rewrite output");

      if (hasMonacoRange && editor && model) {
        // Monaco path: use executeEdits
        lastRewriteSnapshotRef.current = model.getValue();
        editor.executeEdits("ai-rewrite", [
          {
            range: sel.range,
            text: replacement,
            forceMoveMarkers: true,
          },
        ]);
        setEditContent(model.getValue());
      } else {
        // Tiptap/WYSIWYG path: find and replace in editContent
        lastRewriteSnapshotRef.current = editContent;
        const newContent = editContent.replace(sel.selectedText, replacement);
        setEditContent(newContent);
      }
      
      setCanUndoRewrite(true);
      pendingSelectionRef.current = null;
      setRewriteOpen(false);
      setRewritePrompt("");
    } catch (e) {
      setRewriteError(e instanceof Error ? e.message : "Rewrite failed");
    } finally {
      setRewriteRunning(false);
    }
  };

  return (
    <div className={`relative flex flex-col h-full transition-all duration-300 ${isFlashing ? "ring-2 ring-green-500 ring-opacity-75 bg-green-50 dark:bg-green-900/20" : ""}`}>
      {/* Flash indicator */}
      {isFlashing && (
        <div className="absolute top-2 right-2 z-20 flex items-center gap-1 px-2 py-1 bg-green-500 text-white text-xs font-medium rounded-full animate-pulse">
          <span>✓</span>
          <span>Updated</span>
        </div>
      )}
      {/* Minimal Header - just filename and action buttons */}
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        {isEditingTitle ? (
          <input
            ref={titleInputRef}
            type="text"
            value={editedTitle}
            onChange={(e) => setEditedTitle(e.target.value)}
            onBlur={handleTitleSave}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleTitleSave();
              if (e.key === 'Escape') {
                setIsEditingTitle(false);
                setEditedTitle("");
              }
            }}
            disabled={isSavingTitle}
            className="text-sm font-medium text-gray-900 dark:text-gray-100 flex-1 min-w-0 bg-white dark:bg-gray-700 border border-blue-500 rounded px-2 py-0.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        ) : (
          <h3
            className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate flex-1 min-w-0 cursor-pointer hover:text-blue-600 dark:hover:text-blue-400"
            onClick={() => {
              if (!isLocal) {
                setEditedTitle(artifact.display_name);
                setIsEditingTitle(true);
              }
            }}
            title={isLocal ? artifact.display_name : "Click to rename"}
          >
            {artifact.display_name}
          </h3>
        )}

        {/* Word count display */}
        {canShowEditor && totalWordCount > 0 && (
          <span className="text-xs text-gray-500 dark:text-gray-400 flex-shrink-0 ml-2">
            {selectedWordCount !== null ? (
              <span title={`${selectedWordCount} of ${totalWordCount} words selected`}>
                <span className="text-blue-600 dark:text-blue-400 font-medium">{selectedWordCount}</span>
                <span className="mx-0.5">/</span>
                <span>{totalWordCount}</span>
                <span className="ml-0.5">words</span>
              </span>
            ) : (
              <span title={`${totalWordCount} words total`}>
                {totalWordCount} words
              </span>
            )}
          </span>
        )}

        <div className="flex items-center gap-1.5 flex-shrink-0">
          {/* Maximize/Minimize button */}
          <button
            onClick={toggleEditorMaximized}
            className="p-1.5 rounded border border-gray-300 dark:border-gray-500 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
            title={isEditorMaximized ? "Restore panels" : "Maximize editor"}
          >
            {isEditorMaximized ? (
              <Minimize2 className="h-3.5 w-3.5" />
            ) : (
              <Maximize2 className="h-3.5 w-3.5" />
            )}
          </button>

          {canShowEditor && !isEditing && (
            <button
              onClick={handleStartEdit}
              disabled={truncated}
              title={truncated ? "Cannot edit truncated content" : "Edit artifact"}
              className="flex items-center px-2.5 py-1 h-7 text-xs font-medium rounded border border-gray-300 dark:border-gray-500 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Pencil className="h-3.5 w-3.5 mr-1" />
              Edit
            </button>
          )}
          {isEditing && (
            <>
              <button
                onClick={handleCancelEdit}
                disabled={isSaving}
                className="flex items-center px-2.5 py-1 h-7 text-xs font-medium rounded border border-gray-300 dark:border-gray-500 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors"
              >
                <X className="h-3.5 w-3.5 mr-1" />
                Cancel
              </button>

              <button
                onClick={handleUndoRewrite}
                disabled={isSaving || !canUndoRewrite}
                title={canUndoRewrite ? "Undo last AI rewrite (Ctrl+Z)" : "Nothing to undo"}
                className="flex items-center px-2.5 py-1 h-7 text-xs font-medium rounded border border-gray-300 dark:border-gray-500 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Undo2 className="h-3.5 w-3.5 mr-1" />
                Undo
              </button>

              <button
                onClick={handleSave}
                disabled={isSaving || !hasChanges}
                className="flex items-center px-2.5 py-1 h-7 text-xs font-medium rounded bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSaving ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                ) : (
                  <Save className="h-3.5 w-3.5 mr-1" />
                )}
                Save
              </button>
            </>
          )}
        </div>
      </div>

      {/* Preview content */}
      <div className="flex-1 overflow-hidden p-4">
        {/* Phase 5: Rewrite modal */}
        {rewriteOpen && (
          <div
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => {
              if (rewriteRunning) return;
              setRewriteOpen(false);
              pendingSelectionRef.current = null;
            }}
          >
            <div
              className="bg-white dark:bg-gray-800 rounded-lg p-4 w-[520px] max-w-[90vw] shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Ask AI to rewrite selection
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">
                Persona: <span className="text-gray-700 dark:text-gray-200">{persona.label}</span>
              </div>

              <textarea
                value={rewritePrompt}
                onChange={(e) => setRewritePrompt(e.target.value)}
                placeholder="e.g., Make this more concise, remove hedging, keep citations"
                className="w-full min-h-[90px] px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={rewriteRunning}
                autoFocus
              />

              {rewriteError && (
                <div className="mt-2 text-xs text-red-600 dark:text-red-400">{rewriteError}</div>
              )}

              <div className="mt-3 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => {
                    if (rewriteRunning) return;
                    setRewriteOpen(false);
                    pendingSelectionRef.current = null;
                  }}
                  className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={rewriteRunning || !rewritePrompt.trim()}
                  onClick={() => void runRewrite(rewritePrompt)}
                  className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {rewriteRunning ? "Rewriting…" : "Rewrite"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Create New Artifact Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowCreateModal(false)}>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 w-96 shadow-xl" onClick={(e) => e.stopPropagation()}>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Create New Artifact</h3>
              
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Filename
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={createArtifactName}
                      onChange={(e) => setCreateArtifactName(e.target.value)}
                      placeholder="artifact-name"
                      className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      autoFocus
                    />
                    <span className="flex items-center text-sm text-gray-500">.md</span>
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Preview ({createArtifactContent.length} chars)
                  </label>
                  <div className="px-3 py-2 border border-gray-200 dark:border-gray-600 rounded-md bg-gray-50 dark:bg-gray-900 text-xs text-gray-600 dark:text-gray-400 max-h-32 overflow-y-auto whitespace-pre-wrap">
                    {createArtifactContent.slice(0, 500)}{createArtifactContent.length > 500 ? "..." : ""}
                  </div>
                </div>
                
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    onClick={() => {
                      setShowCreateModal(false);
                      setCreateArtifactName("");
                      setCreateArtifactContent("");
                    }}
                    className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={async () => {
                      if (!createArtifactName.trim() || !currentSessionId) return;
                      setIsCreatingArtifact(true);
                      try {
                        const filename = `${createArtifactName.trim()}.md`;
                        const res = await fetch(`${API_BASE_URL}/api/v1/sessions/${currentSessionId}/artifacts`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({
                            filename,
                            content: createArtifactContent,
                            artifact_meta: { source: "selection" },
                          }),
                        });
                        if (res.ok) {
                          const newArtifact = await res.json();
                          // Refresh and select new artifact
                          const { setArtifactFlash } = useWorkbenchStore.getState();
                          setSelectedArtifact(newArtifact.id);
                          setArtifactFlash(newArtifact.id);
                        }
                      } catch (e) {
                        console.error("Failed to create artifact:", e);
                      } finally {
                        setIsCreatingArtifact(false);
                        setShowCreateModal(false);
                        setCreateArtifactName("");
                        setCreateArtifactContent("");
                      }
                    }}
                    disabled={!createArtifactName.trim() || isCreatingArtifact}
                    className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isCreatingArtifact ? "Creating..." : "Create"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : isError ? (
          <div className="flex flex-col items-center justify-center h-32 text-red-500">
            <AlertCircle className="h-8 w-8 mb-2" />
            <span className="text-sm">Failed to load preview</span>
            <span className="text-xs text-gray-500">Please try refresh or reselect the artifact.</span>
          </div>
        ) : previewKind === "image" ? (
          <ImagePreview artifact={artifact} />
        ) : canShowEditor ? (
          <div className="h-full border border-gray-200 dark:border-gray-700 rounded-md overflow-hidden bg-white dark:bg-gray-900 relative">
            {isEditing && (
              <div className="absolute top-0 left-0 right-0 px-2 py-1 bg-gray-100 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600 text-xs text-gray-600 dark:text-gray-300 z-10 flex items-center justify-between">
                <span>
                  ✏️ Editing mode {hasChanges && <span className="text-amber-600 dark:text-amber-400">• Unsaved changes</span>}
                </span>
                <button
                  onClick={() => setShowPreviewInEdit(!showPreviewInEdit)}
                  className={`px-2 py-0.5 rounded text-xs transition-colors ${
                    showPreviewInEdit 
                      ? "bg-blue-500 text-white" 
                      : "bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-500"
                  }`}
                  title={showPreviewInEdit ? "Show WYSIWYG editor" : "Show raw markdown"}
                >
                  {showPreviewInEdit ? "✨ WYSIWYG" : "📝 Raw"}
                </button>
              </div>
            )}
            {/* WYSIWYG mode: Tiptap for markdown files in edit mode (default) */}
            {isEditing && previewKind === "markdown" && !showPreviewInEdit ? (
              <div className="h-full overflow-auto pt-7">
                <TiptapEditor
                  initialValue={editContent}
                  onChange={(markdown) => setEditContent(markdown)}
                  onTogglePrompting={(selectedText) => {
                    if (!artifact) return;
                    toggleTextSelection({
                      artifactId: artifact.id,
                      artifactName: artifact.display_name,
                      startLine: 1,
                      endLine: 1,
                      text: selectedText,
                    });
                  }}
                  onToggleEditing={(selectedText) => {
                    if (!artifact) return;
                    toggleEditTargetSelection({
                      artifactId: artifact.id,
                      artifactName: artifact.display_name,
                      startLine: 1,
                      endLine: 1,
                      text: selectedText,
                    });
                  }}
                  onCreateArtifact={(selectedText) => {
                    const words = selectedText.trim().split(/\s+/).slice(0, 5).join("_");
                    const suggestedName = words.replace(/[^a-zA-Z0-9_-]/g, "").substring(0, 30) || "selection";
                    setCreateArtifactName(suggestedName);
                    setCreateArtifactContent(selectedText);
                    setShowCreateModal(true);
                  }}
                  onHighlight={(selectedText) => {
                    // Tiptap handles highlighting internally via toggleHighlight()
                    // This callback is for any additional logic needed
                    console.log("Highlighted:", selectedText);
                  }}
                />
              </div>
            ) : (
            <Editor
              value={displayContent}
              language={editorLanguage}
              theme="vs-light"
              height="100%"
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                wordWrap: "on",
                scrollBeyondLastLine: false,
                readOnly: !isEditing,
                padding: { top: isEditing ? 28 : 8 },
                // Disable Monaco's built-in context menu entirely
                contextmenu: false,
              }}
              onChange={(value) => {
                if (!isEditing) return;
                setEditContent(value ?? "");
              }}
              onMount={(editor) => {
                editorRef.current = editor;

                // Listen for selection changes to update word count
                editor.onDidChangeCursorSelection(() => {
                  const selection = editor.getSelection();
                  const model = editor.getModel();
                  if (selection && !selection.isEmpty() && model) {
                    const selectedText = model.getValueInRange(selection);
                    setSelectedWordCount(countWords(selectedText));
                  } else {
                    setSelectedWordCount(null);
                  }
                });

                // Custom right-click handler for simple academic-friendly menu
                const editorDomNode = editor.getDomNode();
                if (editorDomNode) {
                  editorDomNode.addEventListener("contextmenu", (e: MouseEvent) => {
                    e.preventDefault();
                    e.stopPropagation();

                    const selection = editor.getSelection();
                    const model = editor.getModel();
                    const hasSelection = selection && !selection.isEmpty();

                    // Remove any existing custom menu
                    const existingMenu = document.getElementById("custom-editor-menu");
                    if (existingMenu) existingMenu.remove();

                    // Create custom menu
                    const menu = document.createElement("div");
                    menu.id = "custom-editor-menu";
                    menu.className = "fixed z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-md shadow-lg py-1 min-w-[200px]";
                    menu.style.left = `${e.clientX}px`;
                    menu.style.top = `${e.clientY}px`;

                    const createMenuItem = (label: string, onClick: () => void, disabled = false) => {
                      const item = document.createElement("div");
                      item.className = `px-3 py-1.5 text-sm cursor-pointer ${
                        disabled
                          ? "text-gray-400 dark:text-gray-500 cursor-not-allowed"
                          : "text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                      }`;
                      item.textContent = label;
                      if (!disabled) {
                        item.onclick = () => {
                          onClick();
                          menu.remove();
                        };
                      }
                      return item;
                    };

                    // Toggle for prompting (context/focus)
                    menu.appendChild(
                      createMenuItem(
                        "📌 Toggle for prompting",
                        () => {
                          if (!hasSelection || !model || !artifact) return;
                          const selectedText = model.getValueInRange(selection!);
                          toggleTextSelection({
                            artifactId: artifact.id,
                            artifactName: artifact.display_name,
                            startLine: selection!.startLineNumber,
                            endLine: selection!.endLineNumber,
                            text: selectedText,
                          });
                        },
                        !hasSelection
                      )
                    );

                    // Toggle for editing (B1.7 - Precise Edit)
                    const isThisArtifactEditTarget = editTargetArtifactId === artifact?.id;
                    const isSelectionEditTargeted = isThisArtifactEditTarget && editTargetSelections.some(
                      (s) =>
                        s.artifactId === artifact?.id &&
                        s.startLine === selection?.startLineNumber &&
                        s.endLine === selection?.endLineNumber
                    );

                    menu.appendChild(
                      createMenuItem(
                        isSelectionEditTargeted ? "✏️ Unmark for editing" : "✏️ Toggle for editing",
                        () => {
                          if (!hasSelection || !model || !artifact) return;
                          const selectedText = model.getValueInRange(selection!);
                          
                          // If this artifact is not the edit target, set it first
                          if (!isThisArtifactEditTarget) {
                            setEditTarget(artifact.id);
                          }
                          
                          toggleEditTargetSelection({
                            artifactId: artifact.id,
                            artifactName: artifact.display_name,
                            startLine: selection!.startLineNumber,
                            endLine: selection!.endLineNumber,
                            text: selectedText,
                          });
                        },
                        !hasSelection
                      )
                    );

                    // Create new artifact from selection
                    menu.appendChild(
                      createMenuItem(
                        "📄 Create new artifact",
                        () => {
                          if (!hasSelection || !model) return;
                          const selectedText = model.getValueInRange(selection!);
                          // Generate suggested name from first few words
                          const words = selectedText.trim().split(/\s+/).slice(0, 5).join("_");
                          const suggestedName = words.replace(/[^a-zA-Z0-9_-]/g, "").substring(0, 30) || "selection";
                          setCreateArtifactName(suggestedName);
                          setCreateArtifactContent(selectedText);
                          setShowCreateModal(true);
                        },
                        !hasSelection
                      )
                    );

                    // Divider
                    const divider = document.createElement("div");
                    divider.className = "border-t border-gray-200 dark:border-gray-600 my-1";
                    menu.appendChild(divider);

                    // Basic edit options (only in edit mode)
                    if (isEditingRef.current) {
                      // Phase 5: AI rewrite selection
                      menu.appendChild(
                        createMenuItem(
                          "🤖 Ask AI to rewrite…",
                          () => {
                            if (!hasSelection || !selection || !model) return;
                            const selectedText = model.getValueInRange(selection);
                            pendingSelectionRef.current = { range: selection, selectedText };
                            setRewriteOpen(true);
                            setRewritePrompt("");
                            setRewriteError(null);
                          },
                          !hasSelection
                        )
                      );

                      menu.appendChild(
                        createMenuItem(
                          "📝 Make more academic",
                          () => {
                            if (!hasSelection || !selection || !model) return;
                            const selectedText = model.getValueInRange(selection);
                            pendingSelectionRef.current = { range: selection, selectedText };
                            void runRewrite(
                              "Rewrite to be more academic and concise. Preserve meaning. Keep citations as-is."
                            );
                          },
                          !hasSelection
                        )
                      );

                      menu.appendChild(
                        createMenuItem(
                          "🔎 Simplify",
                          () => {
                            if (!hasSelection || !selection || !model) return;
                            const selectedText = model.getValueInRange(selection);
                            pendingSelectionRef.current = { range: selection, selectedText };
                            void runRewrite(
                              "Simplify the wording while preserving meaning. Keep technical terms and citations."
                            );
                          },
                          !hasSelection
                        )
                      );

                      // Highlight selection in yellow
                      menu.appendChild(
                        createMenuItem(
                          "🟡 Highlight",
                          () => {
                            if (!hasSelection || !selection || !model) return;
                            const selectedText = model.getValueInRange(selection);
                            // Wrap with HTML mark tag for yellow highlight
                            const highlightedText = `<mark>${selectedText}</mark>`;
                            editor.executeEdits("highlight", [
                              {
                                range: selection,
                                text: highlightedText,
                                forceMoveMarkers: true,
                              },
                            ]);
                            // Update edit content state
                            setEditContent(model.getValue());
                          },
                          !hasSelection
                        )
                      );

                      const divider2 = document.createElement("div");
                      divider2.className = "border-t border-gray-200 dark:border-gray-600 my-1";
                      menu.appendChild(divider2);

                      menu.appendChild(
                        createMenuItem(
                          "Cut",
                          () => {
                            document.execCommand("cut");
                          },
                          !hasSelection
                        )
                      );
                      menu.appendChild(
                        createMenuItem(
                          "Copy",
                          () => {
                            document.execCommand("copy");
                          },
                          !hasSelection
                        )
                      );
                      menu.appendChild(
                        createMenuItem("Paste", () => {
                          document.execCommand("paste");
                        })
                      );
                    } else {
                      menu.appendChild(
                        createMenuItem("Copy", () => {
                          document.execCommand("copy");
                        }, !hasSelection)
                      );
                    }

                    document.body.appendChild(menu);

                    // Close menu on click outside
                    const closeMenu = (ev: MouseEvent) => {
                      if (!menu.contains(ev.target as Node)) {
                        menu.remove();
                        document.removeEventListener("click", closeMenu);
                      }
                    };
                    setTimeout(() => document.addEventListener("click", closeMenu), 0);
                  });
                }

                // Apply decorations for existing selections
                updateDecorations(editor, artifact?.id);
              }}
            />
            )}
            {truncated && !isEditing && (
              <div className="px-3 py-2 text-xs text-amber-600 border-t border-gray-200 bg-amber-50">
                Content truncated - download for full file
              </div>
            )}
          </div>
        ) : (
          <NoPreview artifact={artifact} />
        )}
      </div>
    </div>
  );
}
