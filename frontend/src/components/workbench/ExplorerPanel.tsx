/**
 * Explorer Panel Component
 *
 * Left sidebar - file/folder tree browser.
 * VS Code-style explorer with:
 * - Root directory selection
 * - Folder navigation
 * - File import to artifacts
 */

"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Folder,
  FileText,
  FileSpreadsheet,
  FileType,
  ChevronRight,
  ChevronLeft,
  RefreshCw,
  Home,
  HardDrive,
  Cloud,
  Download,
  ArrowUp,
  Import,
  Check,
  AlertCircle,
  Plus,
  Pin,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils/cn";
import {
  getRoots,
  browseDirectory,
  importFile,
  isImportable,
  getExplorerCapabilities,
  getImportables,
  type FileItem,
  type RootDirectory,
  type DirectoryListing,
  type ExplorerCapabilities,
} from "@/lib/api/explorer";
import { useWorkbenchStore } from "@/lib/store";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";

// File type icons
function getFileIcon(extension: string) {
  switch (extension?.toLowerCase()) {
    case ".xlsx":
    case ".xls":
    case ".csv":
      return <FileSpreadsheet className="h-4 w-4 text-green-600 flex-shrink-0" />;
    case ".docx":
    case ".doc":
      return <FileType className="h-4 w-4 text-blue-600 flex-shrink-0" />;
    case ".pdf":
      return <FileType className="h-4 w-4 text-red-600 flex-shrink-0" />;
    case ".md":
      return <FileText className="h-4 w-4 text-purple-600 flex-shrink-0" />;
    case ".json":
      return <FileText className="h-4 w-4 text-yellow-600 flex-shrink-0" />;
    default:
      return <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />;
  }
}

// Root directory icons
function getRootIcon(icon: string) {
  switch (icon) {
    case "home":
      return <Home className="h-4 w-4" />;
    case "cloud":
      return <Cloud className="h-4 w-4" />;
    case "download":
      return <Download className="h-4 w-4" />;
    case "hard-drive":
      return <HardDrive className="h-4 w-4" />;
    default:
      return <Folder className="h-4 w-4" />;
  }
}

// Format file size
function formatSize(bytes?: number): string {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

type QuickAccessItem = { name: string; path: string };
const QUICK_ACCESS_KEY = "agentb:quick-access";

interface ExplorerPanelProps {
  onCollapse?: () => void;
}

export function ExplorerPanel({ onCollapse }: ExplorerPanelProps) {
  const [roots, setRoots] = useState<RootDirectory[]>([]);
  const [currentPath, setCurrentPath] = useState<string | null>(null);
  const [listing, setListing] = useState<DirectoryListing | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Selection model: checkbox-based multi-select (files + folders)
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [importing, setImporting] = useState<string | null>(null);
  const [importSuccess, setImportSuccess] = useState<string | null>(null);

  // Quick access (user pinned folders)
  const [quickAccess, setQuickAccess] = useState<QuickAccessItem[]>([]);
  const [isQuickAddOpen, setIsQuickAddOpen] = useState(false);
  const [quickAddPath, setQuickAddPath] = useState("");
  const [quickAddName, setQuickAddName] = useState("");

  const [capabilities, setCapabilities] = useState<ExplorerCapabilities | null>(null);

  // Stage 9: bulk import options
  const [bulkRecursive, setBulkRecursive] = useState(false);
  const [bulkImporting, setBulkImporting] = useState(false);
  const [bulkProgress, setBulkProgress] = useState<{ done: number; total: number } | null>(null);
  const [bulkSummary, setBulkSummary] = useState<{ ok: number; failed: number; errors: string[] } | null>(null);

  // Sorting
  type SortKey = "name" | "date" | "type";
  type SortDir = "asc" | "desc";
  const [sortKey, setSortKey] = useState<SortKey>("name");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Get current session from store
  const currentSessionId = useWorkbenchStore((s) => s.currentSessionId);
  const setSelectedArtifact = useWorkbenchStore((s) => s.setSelectedArtifact);
  const queryClient = useQueryClient();

  const persistQuickAccess = useCallback((items: QuickAccessItem[]) => {
    setQuickAccess(items);
    try {
      localStorage.setItem(QUICK_ACCESS_KEY, JSON.stringify(items));
    } catch {
      // ignore
    }
  }, []);

  const loadQuickAccess = useCallback(() => {
    try {
      const raw = localStorage.getItem(QUICK_ACCESS_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as QuickAccessItem[];
      if (Array.isArray(parsed)) {
        setQuickAccess(
          parsed
            .filter((x) => x && typeof x.path === "string" && typeof x.name === "string")
            .slice(0, 30)
        );
      }
    } catch {
      // ignore
    }
  }, []);

  const addQuickAccess = useCallback(
    (item: QuickAccessItem) => {
      const trimmedPath = item.path.trim();
      const trimmedName = item.name.trim() || trimmedPath.split(/[/\\]/).filter(Boolean).slice(-1)[0] || trimmedPath;
      if (!trimmedPath) return;

      const next = [
        { name: trimmedName, path: trimmedPath },
        ...quickAccess.filter((q) => q.path !== trimmedPath),
      ].slice(0, 30);
      persistQuickAccess(next);
    },
    [persistQuickAccess, quickAccess]
  );

  const removeQuickAccess = useCallback(
    (path: string) => {
      persistQuickAccess(quickAccess.filter((q) => q.path !== path));
    },
    [persistQuickAccess, quickAccess]
  );

  // Load roots + capabilities on mount
  useEffect(() => {
    loadRoots();
    loadCapabilities();
    loadQuickAccess();
  }, [loadQuickAccess]);

  const loadRoots = async () => {
    try {
      const data = await getRoots();
      setRoots(data);
    } catch (err) {
      console.error("Failed to load roots:", err);
    }
  };

  const loadCapabilities = async () => {
    try {
      const data = await getExplorerCapabilities();
      setCapabilities(data);
    } catch (err) {
      // Capabilities is optional; don't block explorer
      console.warn("Failed to load explorer capabilities:", err);
      setCapabilities(null);
    }
  };

  const navigateTo = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await browseDirectory(path);
      if (data.error) {
        setError(data.error);
      } else {
        setListing(data);
        setCurrentPath(path);
        // Clear selection on navigation to avoid confusing cross-folder selections
        setSelectedPaths(new Set());
      }
    } catch (err) {
      setError("Failed to load directory");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  const goUp = () => {
    if (listing?.parent) {
      navigateTo(listing.parent);
    } else {
      // Go back to roots view
      setCurrentPath(null);
      setListing(null);
    }
  };

  const toggleSelected = useCallback((path: string, checked?: boolean) => {
    setSelectedPaths((prev) => {
      const next = new Set(prev);
      const shouldSelect = checked ?? !next.has(path);
      if (shouldSelect) next.add(path);
      else next.delete(path);
      return next;
    });
  }, []);

  const handleItemClick = (item: FileItem) => {
    // Click-to-navigate for folders; selection is via checkbox
    if (item.type === "folder") {
      navigateTo(item.path);
      return;
    }

    // For files: click selects single (like VSCode), checkbox allows multi.
    setSelectedPaths(new Set([item.path]));
  };

  const handleImport = async (item: FileItem) => {
    if (!currentSessionId) {
      setError("No session selected");
      return;
    }

    setImporting(item.path);
    setImportSuccess(null);
    try {
      const result = await importFile(item.path, currentSessionId);
      if (result.success) {
        setImportSuccess(item.path);
        setTimeout(() => setImportSuccess(null), 2000);

        // Refresh artifacts panel (React Query)
        queryClient.invalidateQueries({ queryKey: ["session-artifacts", currentSessionId] });
        queryClient.invalidateQueries({ queryKey: ["run-artifacts"] });

        // Stage 7: auto-select the newly imported artifact so preview opens
        const firstArtifactId = result.artifacts?.[0]?.artifact_id;
        if (firstArtifactId) {
          setSelectedArtifact(firstArtifactId);
        }
      } else {
        setError(result.error || "Import failed");
      }
    } catch (err) {
      setError("Failed to import file");
      console.error(err);
    } finally {
      setImporting(null);
    }
  };

  const handleContextMenu = (e: React.MouseEvent, item: FileItem) => {
    e.preventDefault();
    if (item.type === "file" && isImportable(item.extension || "")) {
      handleImport(item);
    }
  };

  const handleImportFolder = async () => {
    if (!currentSessionId) {
      setError("No session selected");
      return;
    }

    // UX: default to current folder; if exactly one folder is selected, use it.
    const selectedFolders = listing?.items
      ?.filter((i) => i.type === "folder" && selectedPaths.has(i.path))
      .map((i) => i.path) || [];

    const folderToImport =
      selectedFolders.length === 1 ? selectedFolders[0] : currentPath;

    if (!folderToImport) {
      setError("No folder selected");
      return;
    }

    if (selectedFolders.length > 1) {
      setError("Please select only one folder (or none, to use current folder)");
      return;
    }

    setBulkImporting(true);
    setBulkSummary(null);
    setError(null);

    try {
      const list = await getImportables(folderToImport, bulkRecursive);
      const files = list.files || [];

      if (files.length === 0) {
        setError("No importable files found in folder");
        return;
      }

      setBulkProgress({ done: 0, total: files.length });

      // Stage 1 polish: keep going on failures + optional concurrency
      const CONCURRENCY = 4;
      let okCount = 0;
      let failCount = 0;
      const errors: string[] = [];

      let idx = 0;
      const worker = async () => {
        while (true) {
          const myIdx = idx;
          idx += 1;
          if (myIdx >= files.length) return;

          const filePath = files[myIdx];
          try {
            const r = await importFile(filePath, currentSessionId);
            if (!r.success) {
              failCount += 1;
              errors.push(`${filePath}: ${r.error || "Import failed"}`);
            } else {
              okCount += 1;
            }
          } catch (e) {
            failCount += 1;
            errors.push(`${filePath}: ${(e as Error).message || "Import failed"}`);
          } finally {
            setBulkProgress((p) =>
              p ? { done: Math.min(p.done + 1, p.total), total: p.total } : null
            );
          }
        }
      };

      const workers = Array.from({ length: Math.min(CONCURRENCY, files.length) }, () =>
        worker()
      );
      await Promise.all(workers);

      setBulkSummary({ ok: okCount, failed: failCount, errors: errors.slice(0, 5) });

      // Refresh artifacts panel
      queryClient.invalidateQueries({ queryKey: ["session-artifacts", currentSessionId] });
      queryClient.invalidateQueries({ queryKey: ["run-artifacts"] });

      if (failCount > 0) {
        setError(`Bulk import finished with ${failCount} failures (see summary)`);
      }
    } catch (err) {
      console.error(err);
      setError("Bulk import failed");
    } finally {
      setBulkImporting(false);
      setTimeout(() => setBulkProgress(null), 1500);
    }
  };

  // Render roots view
  const renderRoots = () => (
    <div className="py-2">
      <div className="px-3 py-1 flex items-center justify-between">
        <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
          Quick Access
        </div>
        <button
          type="button"
          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-300"
          title="Add quick access folder"
          onClick={() => {
            setQuickAddName("");
            setQuickAddPath("");
            setIsQuickAddOpen(true);
          }}
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      {/* User pinned shortcuts */}
      {quickAccess.length > 0 && (
        <div className="mb-2">
          {quickAccess.map((q) => (
            <div
              key={q.path}
              className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title={q.path}
              onClick={() => navigateTo(q.path)}
            >
              <Pin className="h-4 w-4 text-purple-500 flex-shrink-0" />
              <span className="flex-1 truncate text-gray-900 dark:text-gray-100">{q.name}</span>
              <button
                type="button"
                className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400"
                title="Remove"
                onClick={(e) => {
                  e.stopPropagation();
                  removeQuickAccess(q.path);
                }}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Built-in roots */}
      {roots.map((root) => (
        <div
          key={root.path}
          className="flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          onClick={() => navigateTo(root.path)}
        >
          <span className="text-gray-500 dark:text-gray-300">{getRootIcon(root.icon)}</span>
          <span className="text-sm truncate text-gray-900 dark:text-gray-100">{root.name}</span>
        </div>
      ))}
    </div>
  );

  const extensionOk = useMemo(() => {
    const m = new Map<string, boolean>();
    for (const c of capabilities?.checks || []) {
      for (const ext of c.extensions || []) {
        m.set(ext.toLowerCase(), !!c.ok);
      }
    }
    return m;
  }, [capabilities]);

  const getCapabilityDetail = useCallback(
    (extension: string) => {
      const ext = extension.toLowerCase();
      const check = capabilities?.checks?.find((c) =>
        (c.extensions || []).some((e) => e.toLowerCase() === ext)
      );
      return check;
    },
    [capabilities]
  );

  const selectedItems = useMemo(() => {
    if (!listing) return [] as FileItem[];
    return listing.items.filter((i) => selectedPaths.has(i.path));
  }, [listing, selectedPaths]);

  const selectedFilePaths = useMemo(() => {
    return selectedItems
      .filter((i) => i.type === "file" && isImportable((i.extension || "").toLowerCase()))
      .map((i) => i.path);
  }, [selectedItems]);

  // Import selected files (checkbox multi-select)
  const handleImportSelectedFiles = async () => {
    if (!currentSessionId) {
      setError("No session selected");
      return;
    }
    if (selectedFilePaths.length === 0) {
      setError("No files selected");
      return;
    }

    setBulkImporting(true);
    setBulkSummary(null);
    setError(null);

    try {
      const files = selectedFilePaths;
      setBulkProgress({ done: 0, total: files.length });

      const CONCURRENCY = 4;
      let okCount = 0;
      let failCount = 0;
      const errors: string[] = [];

      let idx = 0;
      const worker = async () => {
        while (true) {
          const myIdx = idx;
          idx += 1;
          if (myIdx >= files.length) return;

          const filePath = files[myIdx];
          try {
            const r = await importFile(filePath, currentSessionId);
            if (!r.success) {
              failCount += 1;
              errors.push(`${filePath}: ${r.error || "Import failed"}`);
            } else {
              okCount += 1;
            }
          } catch (e) {
            failCount += 1;
            errors.push(`${filePath}: ${(e as Error).message || "Import failed"}`);
          } finally {
            setBulkProgress((p) =>
              p ? { done: Math.min(p.done + 1, p.total), total: p.total } : null
            );
          }
        }
      };

      await Promise.all(
        Array.from({ length: Math.min(CONCURRENCY, files.length) }, () => worker())
      );

      setBulkSummary({ ok: okCount, failed: failCount, errors: errors.slice(0, 5) });

      queryClient.invalidateQueries({ queryKey: ["session-artifacts", currentSessionId] });
      queryClient.invalidateQueries({ queryKey: ["run-artifacts"] });

      if (failCount > 0) {
        setError(`Import finished with ${failCount} failures (see summary)`);
      }
    } catch (err) {
      console.error(err);
      setError("Import selected failed");
    } finally {
      setBulkImporting(false);
      setTimeout(() => setBulkProgress(null), 1500);
    }
  };

  // Render file/folder item
  const renderItem = (item: FileItem) => {
    const isSelected = selectedPaths.has(item.path);
    const isImporting = importing === item.path;
    const isImported = importSuccess === item.path;

    const ext = (item.extension || "").toLowerCase();
    const basicImportable = item.type === "file" && isImportable(ext);
    const capOk = ext ? extensionOk.get(ext) !== false : true; // default allow if unknown
    const canImport = basicImportable && capOk;
    const capDetail = ext ? getCapabilityDetail(ext) : null;

    return (
      <div
        key={item.path}
        className={cn(
          "flex items-center gap-2 px-3 py-1.5 cursor-pointer text-sm group",
          "hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors",
          isSelected && "bg-blue-50 dark:bg-gray-800 text-blue-700 dark:text-blue-300"
        )}
        onClick={() => handleItemClick(item)}
        onContextMenu={(e) => handleContextMenu(e, item)}
        title={item.path}
      >
        {/* Checkbox selection (multi-select) */}
        <input
          type="checkbox"
          className="h-3.5 w-3.5"
          checked={isSelected}
          onChange={(e) => toggleSelected(item.path, e.target.checked)}
          onClick={(e) => e.stopPropagation()}
          aria-label={`Select ${item.name}`}
        />

        {/* Icon */}
        {item.type === "folder" ? (
          <Folder className="h-4 w-4 text-yellow-500 flex-shrink-0" />
        ) : (
          getFileIcon(item.extension || "")
        )}

        {/* Name */}
        <span className="flex-1 truncate text-gray-900 dark:text-gray-100">{item.name}</span>

        {/* Size (files only) */}
        {item.type === "file" && item.size !== undefined && (
          <span className="text-xs text-gray-400 hidden group-hover:block">
            {formatSize(item.size)}
          </span>
        )}

        {/* Import button */}
        {basicImportable && (
          <button
            className={cn(
              "p-1 rounded transition-colors",
              !canImport && "opacity-30 cursor-not-allowed",
              isImported
                ? "text-green-600"
                : isImporting
                ? "text-blue-500 animate-pulse"
                : "text-gray-400 hover:text-blue-600 hover:bg-blue-50 opacity-0 group-hover:opacity-100"
            )}
            onClick={(e) => {
              e.stopPropagation();
              if (canImport) handleImport(item);
            }}
            title={
              canImport
                ? "Import as Artifact"
                : capDetail?.remediation
                ? `Import disabled: ${capDetail.detail}. Fix: ${capDetail.remediation}`
                : capDetail?.detail
                ? `Import disabled: ${capDetail.detail}`
                : "Import disabled"
            }
            disabled={isImporting || !canImport}
          >
            {isImported ? (
              <Check className="h-3.5 w-3.5" />
            ) : (
              <Import className="h-3.5 w-3.5" />
            )}
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between px-2 py-1 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <span className="text-[11px] font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wide">
          Explorer
        </span>
        <div className="flex items-center gap-0.5">
          {currentPath && (
            <>
              <button
                className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
                title="Go Up"
                onClick={goUp}
              >
                <ArrowUp className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
              </button>
              {/* Sort buttons */}
              <div className="flex items-center border-l border-gray-300 dark:border-gray-600 ml-1 pl-1">
                <button
                  className={cn(
                    "px-1.5 py-0.5 text-[10px] rounded transition-colors",
                    sortKey === "name" ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300" : "text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700"
                  )}
                  title={`Sort by Name (${sortKey === "name" ? (sortDir === "asc" ? "A→Z" : "Z→A") : "click to sort"})`}
                  onClick={() => {
                    if (sortKey === "name") {
                      setSortDir(sortDir === "asc" ? "desc" : "asc");
                    } else {
                      setSortKey("name");
                      setSortDir("asc");
                    }
                  }}
                >
                  A{sortKey === "name" && (sortDir === "asc" ? "↓" : "↑")}
                </button>
                <button
                  className={cn(
                    "px-1.5 py-0.5 text-[10px] rounded transition-colors",
                    sortKey === "date" ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300" : "text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700"
                  )}
                  title={`Sort by Date (${sortKey === "date" ? (sortDir === "asc" ? "Old→New" : "New→Old") : "click to sort"})`}
                  onClick={() => {
                    if (sortKey === "date") {
                      setSortDir(sortDir === "asc" ? "desc" : "asc");
                    } else {
                      setSortKey("date");
                      setSortDir("desc");
                    }
                  }}
                >
                  D{sortKey === "date" && (sortDir === "asc" ? "↓" : "↑")}
                </button>
                <button
                  className={cn(
                    "px-1.5 py-0.5 text-[10px] rounded transition-colors",
                    sortKey === "type" ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300" : "text-gray-500 hover:bg-gray-200 dark:hover:bg-gray-700"
                  )}
                  title={`Sort by Type (${sortKey === "type" ? (sortDir === "asc" ? "A→Z" : "Z→A") : "click to sort"})`}
                  onClick={() => {
                    if (sortKey === "type") {
                      setSortDir(sortDir === "asc" ? "desc" : "asc");
                    } else {
                      setSortKey("type");
                      setSortDir("asc");
                    }
                  }}
                >
                  T{sortKey === "type" && (sortDir === "asc" ? "↓" : "↑")}
                </button>
              </div>
            </>
          )}
          <button
            className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
            title="Refresh"
            onClick={() => currentPath ? navigateTo(currentPath) : loadRoots()}
          >
            <RefreshCw className={cn("h-3.5 w-3.5 text-gray-500 dark:text-gray-400", loading && "animate-spin")} />
          </button>
          {onCollapse && (
            <button
              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
              title="Collapse Explorer"
              onClick={onCollapse}
            >
              <ChevronLeft className="h-4 w-4 text-gray-600 dark:text-gray-300" />
            </button>
          )}
        </div>
      </div>

      {/* Breadcrumb / Path */}
      {currentPath && (
        <div className="px-3 py-1.5 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 space-y-1">
          <div className="flex items-center gap-1">
            <button
              className="text-xs text-blue-600 hover:underline"
              onClick={() => {
                setCurrentPath(null);
                setListing(null);
                setSelectedPaths(new Set());
              }}
            >
              Roots
            </button>
            <ChevronRight className="h-3 w-3 text-gray-400" />
            <span className="text-xs text-gray-600 dark:text-gray-300 truncate" title={currentPath}>
              {currentPath.split(/[/\\]/).slice(-2).join(" / ")}
            </span>
          </div>

          {/* Stage 9: bulk import controls for current folder */}
          <div className="flex items-center gap-2">
            {(() => {
              const isPinned = currentPath ? quickAccess.some((q) => q.path === currentPath) : false;
              return (
                <button
                  type="button"
                  className={cn(
                    "text-[11px] px-2 py-1 rounded border transition-all",
                    isPinned
                      ? "bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-600"
                      : "bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-100 border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
                  )}
                  title={isPinned ? "Unpin from Quick Access" : "Pin to Quick Access"}
                  onClick={() => {
                    if (!currentPath) return;
                    if (isPinned) {
                      removeQuickAccess(currentPath);
                    } else {
                      addQuickAccess({ name: currentPath.split(/[/\\]/).filter(Boolean).slice(-1)[0] || currentPath, path: currentPath });
                    }
                  }}
                >
                  <Pin className={cn("h-3.5 w-3.5 inline-block mr-1", isPinned && "fill-current")} />
                  {isPinned ? "Pinned" : "Pin"}
                </button>
              );
            })()}
            <label className="flex items-center gap-1 text-[11px] text-gray-600 dark:text-gray-300 select-none">
              <input
                type="checkbox"
                className="h-3 w-3"
                checked={bulkRecursive}
                onChange={(e) => setBulkRecursive(e.target.checked)}
              />
              include subfolders
            </label>

            <button
              className={cn(
                "text-[11px] px-2 py-1 rounded border",
                bulkImporting
                  ? "bg-gray-200 dark:bg-gray-800 text-gray-500 dark:text-gray-300 border-gray-200 dark:border-gray-700 cursor-not-allowed"
                  : "bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-100 border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
              )}
              disabled={bulkImporting}
              onClick={handleImportFolder}
              title="Import all importable files in the selected folder (or current folder if none selected)"
            >
              {bulkImporting
                ? bulkProgress
                  ? `Importing ${bulkProgress.done}/${bulkProgress.total}`
                  : "Importing..."
                : "Import folder"}
            </button>

            <button
              className={cn(
                "text-[11px] px-2 py-1 rounded border",
                bulkImporting || selectedFilePaths.length === 0
                  ? "bg-gray-200 dark:bg-gray-800 text-gray-500 dark:text-gray-300 border-gray-200 dark:border-gray-700 cursor-not-allowed"
                  : "bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-100 border-gray-300 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-800"
              )}
              disabled={bulkImporting || selectedFilePaths.length === 0}
              onClick={handleImportSelectedFiles}
              title={
                selectedFilePaths.length > 0
                  ? `Import ${selectedFilePaths.length} selected file(s)`
                  : "Select files using the checkboxes"
              }
            >
              Import selected ({selectedFilePaths.length})
            </button>
          </div>
        </div>
      )}

      {/* Bulk summary */}
      {bulkSummary && (
        <div className="px-3 py-2 bg-blue-50 border-b border-blue-200 text-xs text-blue-900">
          <div className="flex items-center justify-between gap-2">
            <span>
              Bulk import: {bulkSummary.ok} ok, {bulkSummary.failed} failed
            </span>
            <button
              className="text-xs text-blue-700 hover:underline"
              onClick={() => setBulkSummary(null)}
            >
              Dismiss
            </button>
          </div>
          {bulkSummary.errors.length > 0 && (
            <ul className="mt-1 list-disc pl-5 text-blue-800">
              {bulkSummary.errors.map((e) => (
                <li key={e} className="truncate" title={e}>
                  {e}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="px-3 py-2 bg-red-50 border-b border-red-200 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 text-red-500" />
          <span className="text-xs text-red-700">{error}</span>
          <button
            className="ml-auto text-xs text-red-600 hover:underline"
            onClick={() => setError(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <RefreshCw className="h-5 w-5 text-gray-400 animate-spin" />
          </div>
        ) : !currentPath ? (
          renderRoots()
        ) : listing?.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-400">
            <Folder className="h-8 w-8 mb-2" />
            <span className="text-sm">Empty folder</span>
          </div>
        ) : (
          <div className="py-1">
            {listing?.items
              .slice()
              .sort((a, b) => {
                // Folders always first
                if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1;
                
                let cmp = 0;
                if (sortKey === "name") {
                  cmp = a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
                } else if (sortKey === "date") {
                  const aTime = a.modified ? new Date(a.modified).getTime() : 0;
                  const bTime = b.modified ? new Date(b.modified).getTime() : 0;
                  cmp = aTime - bTime;
                } else if (sortKey === "type") {
                  const aExt = a.name.includes(".") ? a.name.split(".").pop() || "" : "";
                  const bExt = b.name.includes(".") ? b.name.split(".").pop() || "" : "";
                  cmp = aExt.localeCompare(bExt, undefined, { sensitivity: "base" });
                }
                return sortDir === "asc" ? cmp : -cmp;
              })
              .map(renderItem)}
          </div>
        )}
      </div>

      {/* Quick Access Add Modal */}
      <Modal
        isOpen={isQuickAddOpen}
        onClose={() => setIsQuickAddOpen(false)}
        title="Add Quick Access"
        size="md"
      >
        <div className="space-y-3">
          <Input
            label="Name (optional)"
            value={quickAddName}
            onChange={(e) => setQuickAddName(e.target.value)}
            placeholder="e.g., Literature Review"
          />
          <Input
            label="Folder path"
            value={quickAddPath}
            onChange={(e) => setQuickAddPath(e.target.value)}
            placeholder="Paste a folder path (e.g., C:\\Users\\...\\Desktop\\AI\\Library)"
          />
          <div className="flex items-center justify-end gap-2 pt-2">
            <button
              type="button"
              className="px-3 py-2 text-sm rounded border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
              onClick={() => setIsQuickAddOpen(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
              onClick={() => {
                addQuickAccess({ name: quickAddName, path: quickAddPath });
                setIsQuickAddOpen(false);
              }}
              disabled={!quickAddPath.trim()}
            >
              Add
            </button>
          </div>

          <div className="text-xs text-gray-500 dark:text-gray-400">
            Tip: You can also browse to a folder in Explorer and click <b>Pin</b>.
          </div>
        </div>
      </Modal>

      {/* Footer removed (wasted space / misleading right-click tip) */}
    </div>
  );
}
