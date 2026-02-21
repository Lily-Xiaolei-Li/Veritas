/**
 * VF Manager Panel Component
 *
 * Integrated VF (Virtual Fieldwork) Middleware Manager for profile generation and sync.
 * Extracted from /vf-middleware page for ConsolePanel integration.
 */

"use client";

import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  deleteVFProfile,
  fetchVFAgents,
  fetchVFList,
  fetchVFStats,
  generateVFProfile,
  lookupVFProfile,
  syncVFProfiles,
} from "@/lib/api/vfMiddleware";
import { LibraryToolsSection } from "./LibraryToolsSection";

// Type definitions
interface VFStats {
  total_profiles: number;
  in_library: number;
  external: number;
  [key: string]: unknown;
}

interface VFItem {
  paper_id: string;
  title?: string;
  year?: number;
  in_library?: boolean;
}

interface VFAgent {
  name: string;
  description: string;
}

interface VFProfile {
  chunks?: Record<string, string>;
  [key: string]: unknown;
}

const CHUNKS = [
  "meta",
  "abstract",
  "theory",
  "literature",
  "research_questions",
  "contributions",
  "key_concepts",
  "cited_for",
];

export function VFManagerPanel() {
  const [stats, setStats] = useState<VFStats | null>(null);
  const [items, setItems] = useState<VFItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "in_library" | "external">("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detailMap, setDetailMap] = useState<Record<string, VFProfile>>({});
  const [detailLoading, setDetailLoading] = useState<string | null>(null);
  const [toast, setToast] = useState<string>("");

  const [agents, setAgents] = useState<VFAgent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState("helper");
  const [showGenerate, setShowGenerate] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [form, setForm] = useState({ paper_id: "", abstract: "", full_text: "", metadata: "{}", in_library: true });

  const [syncing, setSyncing] = useState(false);
  const [syncProgress, setSyncProgress] = useState({ processed: 0, total: 0, current: "", summary: "" });

  const load = async () => {
    setLoading(true);
    try {
      const [s, l, a] = await Promise.all([fetchVFStats(), fetchVFList(1000, 0), fetchVFAgents()]);
      setStats(s as VFStats);
      setItems((l.items || []) as VFItem[]);
      setAgents((a.agents || []) as VFAgent[]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setToast(`Load failed: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const filteredItems = useMemo(() => {
    const q = query.toLowerCase().trim();
    return items.filter((it) => {
      if (filter === "in_library" && !it.in_library) return false;
      if (filter === "external" && it.in_library) return false;
      if (!q) return true;
      return `${it.paper_id || ""} ${(it.title || "")}`.toLowerCase().includes(q);
    });
  }, [items, query, filter]);

  const handleExpand = async (paperId: string) => {
    if (expanded === paperId) return setExpanded(null);
    setExpanded(paperId);
    if (detailMap[paperId]) return;

    setDetailLoading(paperId);
    try {
      const res = await lookupVFProfile(paperId);
      setDetailMap((prev) => ({ ...prev, [paperId]: res.profile as VFProfile }));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setToast(`Lookup failed: ${msg}`);
    } finally {
      setDetailLoading(null);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const metadata = form.metadata.trim() ? JSON.parse(form.metadata) : {};
      await generateVFProfile({
        paper_id: form.paper_id,
        abstract: form.abstract,
        full_text: form.full_text,
        metadata,
        in_library: form.in_library,
        agent: selectedAgent,
      });
      setToast("Profile generated");
      setShowGenerate(false);
      await load();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setToast(`Generate failed: ${msg}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleFile = async (file?: File | null) => {
    if (!file) return;
    const text = await file.text();
    setForm((prev) => ({ ...prev, full_text: text }));
  };

  const handleSync = async (dryRun = false) => {
    setSyncing(true);
    setSyncProgress({ processed: 0, total: 0, current: "", summary: "" });
    try {
      await syncVFProfiles({ agent: selectedAgent, dry_run: dryRun }, (msg) => {
        const status = String(msg.status || "");
        if (status === "processing") {
          setSyncProgress((prev) => ({
            ...prev,
            processed: Number(msg.processed || prev.processed),
            total: Number(msg.total || prev.total),
            current: String(msg.current_paper || ""),
          }));
        }
        if (status === "done" || status === "dry_run") {
          setSyncProgress((prev) => ({ ...prev, summary: JSON.stringify(msg) }));
        }
      });
      await load();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setToast(`Sync failed: ${msg}`);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="h-full overflow-auto p-3 space-y-3 text-gray-900 dark:text-gray-100">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold">📚 VF Manager</h2>
        <button
          onClick={() => void load()}
          disabled={loading}
          className="text-xs px-2 py-1 border rounded hover:bg-gray-100 dark:hover:bg-gray-800"
        >
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {/* Toast */}
      {toast && (
        <div className="rounded border border-amber-400 bg-amber-50 dark:bg-amber-900/20 px-3 py-2 text-sm flex justify-between items-center">
          <span>{toast}</span>
          <button onClick={() => setToast("")} className="text-gray-500 hover:text-gray-700">×</button>
        </div>
      )}

      {/* Controls */}
      <div className="rounded border p-3 bg-white dark:bg-gray-900 space-y-2">
        <div className="flex flex-wrap gap-2 items-center text-xs">
          <select
            className="border rounded px-2 py-1 bg-transparent"
            value={selectedAgent}
            onChange={(e) => setSelectedAgent(e.target.value)}
          >
            {(agents.length ? agents : [{ name: "helper", description: "default" }]).map((a) => (
              <option key={a.name} value={a.name}>{a.name} - {a.description}</option>
            ))}
          </select>
          <button className="border rounded px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800" onClick={() => setShowGenerate((v) => !v)}>
            Generate
          </button>
          <button className="border rounded px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800" onClick={() => void handleSync(false)} disabled={syncing}>
            Sync
          </button>
          <button className="border rounded px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-800" onClick={() => void handleSync(true)} disabled={syncing}>
            Dry Run
          </button>
        </div>

        {/* Generate Form */}
        {showGenerate && (
          <div className="border rounded p-2 space-y-2 text-xs">
            <input
              className="w-full border rounded px-2 py-1 dark:bg-gray-800"
              placeholder="paper_id"
              value={form.paper_id}
              onChange={(e) => setForm((p) => ({ ...p, paper_id: e.target.value }))}
            />
            <textarea
              className="w-full border rounded px-2 py-1 h-16 dark:bg-gray-800"
              placeholder="abstract"
              value={form.abstract}
              onChange={(e) => setForm((p) => ({ ...p, abstract: e.target.value }))}
            />
            <textarea
              className="w-full border rounded px-2 py-1 h-16 dark:bg-gray-800"
              placeholder="full_text"
              value={form.full_text}
              onChange={(e) => setForm((p) => ({ ...p, full_text: e.target.value }))}
            />
            <input type="file" accept=".md,.txt" onChange={(e) => void handleFile(e.target.files?.[0])} />
            <textarea
              className="w-full border rounded px-2 py-1 h-12 font-mono dark:bg-gray-800"
              placeholder="metadata JSON"
              value={form.metadata}
              onChange={(e) => setForm((p) => ({ ...p, metadata: e.target.value }))}
            />
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={form.in_library} onChange={(e) => setForm((p) => ({ ...p, in_library: e.target.checked }))} />
              in_library
            </label>
            <button
              className="border rounded px-3 py-1 bg-blue-500 text-white hover:bg-blue-600"
              onClick={() => void handleGenerate()}
              disabled={generating}
            >
              {generating ? "Generating..." : "Submit"}
            </button>
          </div>
        )}

        {/* Sync Progress */}
        {syncing && (
          <div className="text-xs space-y-1">
            <div>Syncing... {syncProgress.processed}/{syncProgress.total} {syncProgress.current}</div>
            <div className="h-1.5 bg-gray-200 rounded overflow-hidden">
              <div
                className="h-1.5 bg-blue-500 transition-all"
                style={{ width: `${syncProgress.total ? (syncProgress.processed / syncProgress.total) * 100 : 0}%` }}
              />
            </div>
          </div>
        )}
        {syncProgress.summary && <pre className="text-[10px] overflow-auto border rounded p-2 max-h-20">{syncProgress.summary}</pre>}
      </div>

      {/* Stats */}
      {stats && (
        <div className="rounded border p-3 bg-white dark:bg-gray-900">
          <h3 className="font-semibold text-sm mb-1">Stats</h3>
          <div className="text-xs grid grid-cols-3 gap-2">
            <div className="border rounded p-2 text-center">
              <div className="text-lg font-bold">{stats.total_profiles}</div>
              <div className="text-gray-500">Total</div>
            </div>
            <div className="border rounded p-2 text-center">
              <div className="text-lg font-bold text-green-600">{stats.in_library}</div>
              <div className="text-gray-500">In Library</div>
            </div>
            <div className="border rounded p-2 text-center">
              <div className="text-lg font-bold text-blue-600">{stats.external}</div>
              <div className="text-gray-500">External</div>
            </div>
          </div>
        </div>
      )}

      {/* Library Tools */}
      <LibraryToolsSection />

      {/* Profiles List */}
      <div className="rounded border p-3 bg-white dark:bg-gray-900 space-y-2">
        <h3 className="font-semibold text-sm">Profiles</h3>
        <div className="flex flex-wrap gap-2 text-xs">
          <input
            className="border rounded px-2 py-1 flex-1 min-w-40 dark:bg-gray-800"
            placeholder="Search paper_id or title"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <select
            className="border rounded px-2 py-1 dark:bg-gray-800"
            value={filter}
            onChange={(e) => setFilter(e.target.value as "all" | "in_library" | "external")}
          >
            <option value="all">All</option>
            <option value="in_library">In Library</option>
            <option value="external">External</option>
          </select>
        </div>

        {/* Items */}
        <div className="space-y-1 max-h-80 overflow-auto">
          {filteredItems.slice(0, 100).map((it) => (
            <div key={it.paper_id} className="border rounded px-2 py-1.5 text-xs">
              <div className="flex items-start justify-between gap-2">
                <button className="text-left flex-1" onClick={() => void handleExpand(it.paper_id)}>
                  <div className="font-medium truncate">{it.paper_id}</div>
                  <div className="text-[10px] text-gray-500 truncate">
                    {it.title || "(no title)"} · {it.year || "n/a"} · {it.in_library ? "📚" : "🔗"}
                  </div>
                </button>
                <button
                  className="text-red-500 hover:text-red-700 text-[10px]"
                  onClick={async () => {
                    if (!confirm(`Delete ${it.paper_id}?`)) return;
                    await deleteVFProfile(it.paper_id);
                    await load();
                  }}
                >
                  ×
                </button>
              </div>

              {/* Expanded Detail */}
              {expanded === it.paper_id && (
                <div className="mt-2 grid grid-cols-1 gap-1">
                  {detailLoading === it.paper_id && <div className="text-gray-500">Loading...</div>}
                  {CHUNKS.map((chunkId) => {
                    const chunk = detailMap[it.paper_id]?.chunks?.[chunkId] || "";
                    if (!chunk) return null;
                    return (
                      <div key={chunkId} className="border rounded p-1.5">
                        <div className="inline-block text-[9px] px-1.5 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 mb-1">
                          {chunkId}
                        </div>
                        {chunkId === "meta" ? (
                          <pre className="text-[10px] overflow-auto max-h-20">{chunk}</pre>
                        ) : (
                          <div className="prose prose-xs dark:prose-invert max-w-none text-[11px] max-h-24 overflow-auto">
                            <ReactMarkdown>{chunk}</ReactMarkdown>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
          {filteredItems.length > 100 && (
            <div className="text-[10px] text-gray-500 text-center py-1">
              Showing 100 of {filteredItems.length} profiles
            </div>
          )}
          {!loading && filteredItems.length === 0 && (
            <p className="text-xs text-gray-500 text-center py-2">No profiles found.</p>
          )}
        </div>
      </div>
    </div>
  );
}
