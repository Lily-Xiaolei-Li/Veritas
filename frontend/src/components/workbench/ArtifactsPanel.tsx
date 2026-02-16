/**
 * Artifacts Panel Component (B1.3 - Artifact Handling)
 *
 * Top-right panel with artifacts browsing and preview.
 * Now includes Knowledge Sources buttons (Library RAG, Empiricals RAG, Add Sources).
 */

"use client";

import React, { useState } from "react";
import { BookOpen, Users, Plus, Loader2, Database, X, FileText, Search, Upload, ListChecks, Sparkles } from "lucide-react";
import { ArtifactBrowser } from "../artifacts";
import { ProliferomaximaPanel } from "@/components/proliferomaxima";
import { cn } from "@/lib/utils/cn";
import { API_BASE_URL } from "@/lib/utils/constants";
import { authFetch } from "@/lib/api/authFetch";

// Types for knowledge sources
interface KnowledgeSource {
  name: string;
  display_name: string;
  description: string;
  vectors_count: number;
  points_count: number;
  status: "ready" | "offline" | "error";
  path: string | null;
  error: string | null;
}

interface KnowledgeDocument {
  id: string;
  filename: string;
  chunks: number;
  source_path?: string | null;
}

// Knowledge Source Button Component
function KnowledgeButton({
  icon: Icon,
  label,
  onClick,
  variant = "default",
}: {
  icon: React.ElementType;
  label: string;
  onClick: () => void;
  variant?: "default" | "primary";
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded transition-colors",
        variant === "primary"
          ? "bg-blue-500 text-white hover:bg-blue-600"
          : "bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-600"
      )}
    >
      <Icon className="h-3 w-3" />
      <span>{label}</span>
    </button>
  );
}

// Knowledge Source Modal
function KnowledgeModal({
  source,
  onClose,
  onRefresh,
}: {
  source: KnowledgeSource | null;
  onClose: () => void;
  onRefresh?: () => Promise<void>;
}) {
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState<"stats" | "documents">("stats");
  const [docs, setDocs] = useState<KnowledgeDocument[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [docsError, setDocsError] = useState<string | null>(null);

  // Early return after all hooks
  if (!source) return null;

  const isOnline = source.status === "ready";

  const handleReconnect = async () => {
    if (!onRefresh) return;
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  const fetchDocuments = async () => {
    if (!source) return;
    setDocsLoading(true);
    setDocsError(null);
    try {
      const res = await authFetch(`${API_BASE_URL}/api/v1/knowledge/sources/${source.name}/documents?limit=2000`);
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `HTTP ${res.status}`);
      }
      const data = await res.json();
      setDocs((data.documents || []) as KnowledgeDocument[]);
    } catch (e) {
      setDocsError(e instanceof Error ? e.message : String(e));
      setDocs([]);
    } finally {
      setDocsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-blue-500" />
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">
              {source.display_name}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            <X className="h-4 w-4 text-gray-500" />
          </button>
        </div>

        {/* Tabs */}
        <div className="px-4 pt-3 flex gap-2">
          <button
            onClick={() => setActiveTab("stats")}
            className={cn(
              "px-3 py-1 text-xs rounded",
              activeTab === "stats"
                ? "bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50"
            )}
          >
            Stats
          </button>
          <button
            onClick={async () => {
              setActiveTab("documents");
              if (docs.length === 0 && !docsLoading && !docsError) {
                await fetchDocuments();
              }
            }}
            className={cn(
              "px-3 py-1 text-xs rounded",
              activeTab === "documents"
                ? "bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                : "text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700/50"
            )}
          >
            Documents
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Status */}
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "w-2 h-2 rounded-full",
                isOnline ? "bg-green-500" : "bg-red-500"
              )}
            />
            <span className={cn(
              "text-sm font-medium",
              isOnline ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
            )}>
              {isOnline ? "Online" : source.status === "error" ? "Error" : "Offline"}
            </span>
          </div>

          {activeTab === "stats" ? (
            <>
              {/* Description */}
              <p className="text-sm text-gray-600 dark:text-gray-400">
                {source.description}
              </p>

              {/* Stats */}
              {isOnline && (
                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
                  <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                    {source.points_count.toLocaleString()}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    Chunks indexed
                  </div>
                  <div className="text-[11px] text-gray-400 dark:text-gray-500 mt-1">
                    Click &quot;Documents&quot; tab to see actual document count
                  </div>
                </div>
              )}
            </>
          ) : (
            <>
              {!isOnline ? (
                <p className="text-sm text-gray-500">Source offline.</p>
              ) : docsLoading ? (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading documents…
                </div>
              ) : docsError ? (
                <div className="text-sm text-red-600 dark:text-red-400">{docsError}</div>
              ) : docs.length === 0 ? (
                <p className="text-sm text-gray-500">No documents found.</p>
              ) : (
                <>
                  <div className="text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
                    {docs.length.toLocaleString()} documents
                  </div>
                  <div className="max-h-[280px] overflow-auto border border-gray-200 dark:border-gray-700 rounded">
                  {docs.slice(0, 500).map((d) => (
                    <div
                      key={d.id}
                      className="flex items-center justify-between gap-3 px-3 py-2 text-sm border-b border-gray-100 dark:border-gray-700/50"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <FileText className="h-4 w-4 text-gray-400 flex-shrink-0" />
                        <div className="truncate">
                          <div className="truncate text-gray-800 dark:text-gray-100">{d.filename}</div>
                          {d.source_path ? (
                            <div className="truncate text-[11px] text-gray-400">{d.source_path}</div>
                          ) : null}
                        </div>
                      </div>
                      <div className="text-[11px] text-gray-500 flex-shrink-0">{d.chunks} chunks</div>
                    </div>
                  ))}
                  </div>
                </>
              )}
            </>
          )}

          {/* Error */}
          {source.error && (
            <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3">
              <p className="text-sm text-red-600 dark:text-red-400">{source.error}</p>
            </div>
          )}

          {/* Path */}
          {source.path && (
            <div className="text-xs text-gray-400 dark:text-gray-500 truncate">
              📁 {source.path}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-2">
          {onRefresh && (
            <button
              onClick={handleReconnect}
              disabled={refreshing}
              className={cn(
                "px-3 py-1.5 text-sm font-medium rounded flex items-center gap-1.5",
                refreshing
                  ? "bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed"
                  : "bg-blue-500 text-white hover:bg-blue-600"
              )}
            >
              {refreshing ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <Database className="h-3.5 w-3.5" />
                  {isOnline ? "Refresh" : "Connect"}
                </>
              )}
            </button>
          )}
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

type AddTab = "upload" | "search" | "batch" | "queue";
type SearchItem = { title?: string; authors?: string[]; year?: number; doi?: string; is_open_access?: boolean | null };
type QueueItem = { id: string; kind: string; status: string; progress?: Record<string, string> };

function AddSourcesModal({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<AddTab>("upload");
  const [files, setFiles] = useState<FileList | null>(null);
  const [searchQ, setSearchQ] = useState("");
  const [searchResults, setSearchResults] = useState<SearchItem[]>([]);
  const [batchInput, setBatchInput] = useState("");
  const [queueItems, setQueueItems] = useState<QueueItem[]>([]);
  const [busy, setBusy] = useState(false);

  const refreshQueue = async () => {
    const res = await authFetch(`${API_BASE_URL}/api/v1/knowledge/queue`);
    if (res.ok) {
      const data = await res.json();
      setQueueItems(data.items || []);
    }
  };

  React.useEffect(() => {
    if (tab === "queue") {
      refreshQueue();
      const t = setInterval(refreshQueue, 3000);
      return () => clearInterval(t);
    }
  }, [tab]);

  const handleUpload = async () => {
    if (!files || files.length === 0) return;
    setBusy(true);
    try {
      const fd = new FormData();
      Array.from(files).forEach((f) => fd.append("files", f));
      await authFetch(`${API_BASE_URL}/api/v1/knowledge/upload`, { method: "POST", body: fd });
      setTab("queue");
      await refreshQueue();
    } finally {
      setBusy(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQ.trim()) return;
    setBusy(true);
    try {
      const res = await authFetch(`${API_BASE_URL}/api/v1/knowledge/search?q=${encodeURIComponent(searchQ)}`);
      const data = await res.json();
      setSearchResults(data.items || []);
    } finally {
      setBusy(false);
    }
  };

  const queueDownload = async (item: SearchItem) => {
    setBusy(true);
    try {
      await authFetch(`${API_BASE_URL}/api/v1/knowledge/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ doi: item.doi, title: item.title }),
      });
      setTab("queue");
      await refreshQueue();
    } finally {
      setBusy(false);
    }
  };

  const submitBatch = async () => {
    if (!batchInput.trim()) return;
    setBusy(true);
    try {
      await authFetch(`${API_BASE_URL}/api/v1/knowledge/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dois: batchInput }),
      });
      setTab("queue");
      await refreshQueue();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-3xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Plus className="h-5 w-5 text-blue-500" />
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">Add Knowledge Source</h3>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"><X className="h-4 w-4 text-gray-500" /></button>
        </div>

        <div className="px-4 pt-3 flex gap-2 text-xs">
          {([
            ["upload", "Upload", Upload],
            ["search", "Search", Search],
            ["batch", "Batch Import", FileText],
            ["queue", "Queue", ListChecks],
          ] as Array<[AddTab, string, React.ElementType]>).map(([k, label, Icon]) => (
            <button key={k} onClick={() => setTab(k)} className={cn("px-3 py-1 rounded flex items-center gap-1", tab === k ? "bg-blue-500 text-white" : "bg-gray-100 dark:bg-gray-700")}> <Icon className="h-3 w-3" /> {label}</button>
          ))}
        </div>

        <div className="p-4 min-h-[320px]">
          {tab === "upload" && (
            <div className="space-y-3">
              <input type="file" multiple accept="application/pdf" onChange={(e) => setFiles(e.target.files)} />
              <button onClick={handleUpload} disabled={busy} className="px-3 py-1.5 bg-blue-500 text-white rounded">Upload</button>
            </div>
          )}

          {tab === "search" && (
            <div className="space-y-3">
              <div className="flex gap-2"><input value={searchQ} onChange={(e) => setSearchQ(e.target.value)} className="flex-1 border rounded px-2 py-1 dark:bg-gray-700" placeholder="Search paper title/keyword" /><button onClick={handleSearch} className="px-3 py-1.5 bg-blue-500 text-white rounded">Search</button></div>
              <div className="max-h-[220px] overflow-auto space-y-2">
                {searchResults.map((r, i) => <div key={i} className="border rounded p-2 text-sm"><div className="font-medium">{r.title}</div><div className="text-xs text-gray-500">{(r.authors || []).join(", ")} · {r.year || "N/A"} · DOI: {r.doi || "N/A"} · OA: {String(r.is_open_access ?? "unknown")}</div><button onClick={() => queueDownload(r)} className="mt-2 px-2 py-1 text-xs bg-green-500 text-white rounded">Download</button></div>)}
              </div>
            </div>
          )}

          {tab === "batch" && (
            <div className="space-y-3">
              <textarea value={batchInput} onChange={(e) => setBatchInput(e.target.value)} className="w-full h-40 border rounded p-2 dark:bg-gray-700" placeholder="Paste DOI list (one per line or comma separated)" />
              <button onClick={submitBatch} className="px-3 py-1.5 bg-blue-500 text-white rounded">Start Batch</button>
            </div>
          )}

          {tab === "queue" && (
            <div className="space-y-2 max-h-[260px] overflow-auto">
              {queueItems.map((q) => <div key={q.id} className="border rounded p-2 text-sm"><div className="font-medium">{q.kind} · {q.status}</div><div className="text-xs text-gray-500">Downloading: {q.progress?.downloading} → Parsing: {q.progress?.parsing} → Chunking: {q.progress?.chunking} → Embedding: {q.progress?.embedding} → Indexed: {q.progress?.indexing}</div></div>)}
            </div>
          )}
        </div>

        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex justify-end">
          <button onClick={onClose} className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">Close</button>
        </div>
      </div>
    </div>
  );
}

export function ArtifactsPanel() {
  const [sources, setSources] = useState<KnowledgeSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSource, setSelectedSource] = useState<KnowledgeSource | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showProliferomaxima, setShowProliferomaxima] = useState(false);

  // Fetch knowledge sources
  const fetchSources = async (): Promise<KnowledgeSource[]> => {
    setLoading(true);
    try {
      const res = await authFetch(`${API_BASE_URL}/api/v1/knowledge/sources`);
      if (res.ok) {
        const data = await res.json();
        const newSources = data.sources || [];
        setSources(newSources);
        return newSources;
      }
    } catch (e) {
      console.error("Failed to fetch knowledge sources:", e);
    } finally {
      setLoading(false);
    }
    return [];
  };

  // Fetch on mount
  React.useEffect(() => {
    fetchSources();
  }, []);

  const librarySource = sources.find((s) => s.name === "library");
  const empiricalsSource = sources.find((s) => s.name === "interviews");

  // Knowledge sources UI to pass to ArtifactBrowser
  const knowledgeSourcesUI = (
    <>
      {loading ? (
        <Loader2 className="h-3 w-3 animate-spin text-gray-400" />
      ) : (
        <>
          <KnowledgeButton
            icon={BookOpen}
            label="Library"
            onClick={() => librarySource && setSelectedSource(librarySource)}
          />
          <KnowledgeButton
            icon={Users}
            label="Empiricals"
            onClick={() => empiricalsSource && setSelectedSource(empiricalsSource)}
          />
          <KnowledgeButton
            icon={Plus}
            label="Source"
            onClick={() => setShowAddModal(true)}
            variant="primary"
          />
          <KnowledgeButton
            icon={Sparkles}
            label="Proliferomaxima"
            onClick={() => setShowProliferomaxima(true)}
          />
        </>
      )}
    </>
  );

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
      {/* Tab Content - ArtifactBrowser includes the unified toolbar */}
      <div className="flex-1 overflow-hidden">
        <ArtifactBrowser knowledgeSourcesSlot={knowledgeSourcesUI} />
      </div>

      {/* Modals */}
      {selectedSource && (
        <KnowledgeModal 
          source={selectedSource} 
          onClose={() => setSelectedSource(null)}
          onRefresh={async () => {
            const newSources = await fetchSources();
            // Update selectedSource with refreshed data
            const refreshed = newSources.find(s => s.name === selectedSource.name);
            if (refreshed) setSelectedSource(refreshed);
          }}
        />
      )}
      {showAddModal && (
        <AddSourcesModal onClose={() => setShowAddModal(false)} />
      )}
      {showProliferomaxima && (
        <ProliferomaximaPanel onClose={() => setShowProliferomaxima(false)} />
      )}
    </div>
  );
}
