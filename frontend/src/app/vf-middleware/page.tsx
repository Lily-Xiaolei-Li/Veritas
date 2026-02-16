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

export default function VFMiddlewarePage() {
  const [stats, setStats] = useState<any>(null);
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"all" | "in_library" | "external">("all");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detailMap, setDetailMap] = useState<Record<string, any>>({});
  const [detailLoading, setDetailLoading] = useState<string | null>(null);
  const [toast, setToast] = useState<string>("");

  const [agents, setAgents] = useState<any[]>([]);
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
      setStats(s);
      setItems(l.items || []);
      setAgents(a.agents || []);
    } catch (e: any) {
      setToast(`Load failed: ${e?.message || String(e)}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const [displayLimit, setDisplayLimit] = useState(10);

  const filteredItems = useMemo(() => {
    const q = query.toLowerCase().trim();
    return items
      .filter((it) => {
        if (filter === "in_library" && !it.in_library) return false;
        if (filter === "external" && it.in_library) return false;
        if (!q) return true;
        return `${it.paper_id || ""} ${(it.title || "")}`.toLowerCase().includes(q);
      })
      .sort((a, b) => (b.last_updated || "").localeCompare(a.last_updated || ""));
  }, [items, query, filter]);

  // Reset display limit when search/filter changes
  useEffect(() => { setDisplayLimit(10); }, [query, filter]);

  const visibleItems = filteredItems.slice(0, displayLimit);
  const hasMore = filteredItems.length > displayLimit;

  const handleExpand = async (paperId: string) => {
    if (expanded === paperId) return setExpanded(null);
    setExpanded(paperId);
    if (detailMap[paperId]) return;

    setDetailLoading(paperId);
    try {
      const res = await lookupVFProfile(paperId);
      setDetailMap((prev) => ({ ...prev, [paperId]: res.profile }));
    } catch (e: any) {
      setToast(`Lookup failed: ${e?.message || String(e)}`);
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
    } catch (e: any) {
      setToast(`Generate failed: ${e?.message || String(e)}`);
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
    } catch (e: any) {
      setToast(`Sync failed: ${e?.message || String(e)}`);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <main className="p-4 md:p-6 space-y-4" style={{ color: "var(--theme-text)", background: "var(--theme-bg)" }}>
      <style>{`
        .vf-btn { border: 1px solid var(--theme-border); border-radius: 0.25rem; padding: 0.25rem 0.75rem; font-size: 0.875rem; color: var(--theme-text); background: var(--theme-bg); cursor: pointer; }
        .vf-btn:hover:not(:disabled) { background: var(--theme-bg-secondary); }
        .vf-input { border: 1px solid var(--theme-border); border-radius: 0.25rem; padding: 0.25rem 0.5rem; color: var(--theme-text); background: var(--theme-bg); }
      `}</style>
      <h1 className="text-2xl font-bold">VF Middleware Manager v2</h1>
      {toast && <div className="rounded px-3 py-2 text-sm" style={{ border: "1px solid var(--theme-border)", background: "var(--theme-bg-secondary)" }}>{toast}</div>}
      {loading && <p className="text-sm" style={{ color: "var(--theme-text-muted)" }}>Loading...</p>}

      <div className="rounded p-4 space-y-3" style={{ border: "1px solid var(--theme-border)", background: "var(--theme-bg-secondary)" }}>
        <div className="flex flex-wrap gap-2 items-center">
          <select className="rounded px-2 py-1 text-sm" style={{ border: "1px solid var(--theme-border)", background: "var(--theme-bg)", color: "var(--theme-text)" }} value={selectedAgent} onChange={(e) => setSelectedAgent(e.target.value)}>
            {(agents.length ? agents : [{ name: "helper", description: "default" }]).map((a) => (
              <option key={a.name} value={a.name}>{a.name} - {a.description}</option>
            ))}
          </select>
          <button className="vf-btn" onClick={() => setShowGenerate((v) => !v)}>Generate Profile</button>
          <button className="vf-btn" onClick={() => void handleSync(false)} disabled={syncing}>Sync Library</button>
          <button className="vf-btn" onClick={() => void handleSync(true)} disabled={syncing}>Dry Run Sync</button>
          <button disabled title="This feature is coming in a future update" className="vf-btn opacity-50">Re-analyze All</button>
          <button disabled title="This feature is coming in a future update" className="vf-btn opacity-50">Export Profiles</button>
          <button disabled title="This feature is coming in a future update" className="vf-btn opacity-50">Bulk Compare</button>
        </div>

        {showGenerate && (
          <div className="rounded p-3 space-y-2" style={{ border: "1px solid var(--theme-border)" }}>
            <input className="vf-input w-full" placeholder="paper_id" value={form.paper_id} onChange={(e) => setForm((p) => ({ ...p, paper_id: e.target.value }))} />
            <textarea className="vf-input w-full h-20" placeholder="abstract" value={form.abstract} onChange={(e) => setForm((p) => ({ ...p, abstract: e.target.value }))} />
            <textarea className="vf-input w-full h-24" placeholder="full_text" value={form.full_text} onChange={(e) => setForm((p) => ({ ...p, full_text: e.target.value }))} />
            <input type="file" accept=".md,.txt" onChange={(e) => void handleFile(e.target.files?.[0])} />
            <textarea className="vf-input w-full h-20 font-mono text-xs" placeholder="metadata JSON" value={form.metadata} onChange={(e) => setForm((p) => ({ ...p, metadata: e.target.value }))} />
            <label className="text-sm flex items-center gap-2"><input type="checkbox" checked={form.in_library} onChange={(e) => setForm((p) => ({ ...p, in_library: e.target.checked }))} /> in_library</label>
            <button className="vf-btn" onClick={() => void handleGenerate()} disabled={generating}>{generating ? "Generating profile..." : "Submit"}</button>
          </div>
        )}

        {syncing && (
          <div className="text-sm space-y-1">
            <div>Syncing... {syncProgress.processed}/{syncProgress.total} {syncProgress.current}</div>
            <div className="h-2 bg-gray-200 rounded overflow-hidden"><div className="h-2 bg-blue-500" style={{ width: `${syncProgress.total ? (syncProgress.processed / syncProgress.total) * 100 : 0}%` }} /></div>
          </div>
        )}
        {syncProgress.summary && <pre className="text-xs overflow-auto border rounded p-2">{syncProgress.summary}</pre>}
      </div>

      {stats && (
        <div className="rounded p-4" style={{ border: "1px solid var(--theme-border)", background: "var(--theme-bg-secondary)" }}>
          <h2 className="font-semibold mb-2">Stats</h2>
          <pre className="text-xs overflow-auto">{JSON.stringify(stats, null, 2)}</pre>
        </div>
      )}

      <div className="rounded p-4 space-y-3" style={{ border: "1px solid var(--theme-border)", background: "var(--theme-bg-secondary)" }}>
        <h2 className="font-semibold">Profiles</h2>
        <div className="flex flex-wrap gap-2">
          <input className="rounded px-2 py-1 text-sm min-w-64" style={{ border: "1px solid var(--theme-border)", background: "var(--theme-bg)", color: "var(--theme-text)" }} placeholder="Search paper_id or title" value={query} onChange={(e) => setQuery(e.target.value)} />
          <select className="rounded px-2 py-1 text-sm" style={{ border: "1px solid var(--theme-border)", background: "var(--theme-bg)", color: "var(--theme-text)" }} value={filter} onChange={(e) => setFilter(e.target.value as any)}>
            <option value="all">All</option>
            <option value="in_library">In Library</option>
            <option value="external">External</option>
          </select>
        </div>
        <div className="text-xs mb-1" style={{ color: "var(--theme-text-muted)" }}>
          Showing {visibleItems.length} of {filteredItems.length} profiles {query && `(filtered from ${items.length} total)`}
        </div>
        <div className="space-y-2">
          {visibleItems.map((it) => (
            <div key={it.paper_id} className="rounded px-3 py-2" style={{ border: "1px solid var(--theme-border)" }}>
              <div className="flex items-start justify-between gap-3">
                <button className="text-left" onClick={() => void handleExpand(it.paper_id)}>
                  <div className="font-medium">{it.paper_id}</div>
                  <div className="text-xs" style={{ color: "var(--theme-text-muted)" }}>{it.title || "(no title)"} · {it.year || "n/a"} · {it.in_library ? "In Library" : "External"}</div>
                </button>
                <button
                  className="text-red-600 hover:underline text-sm"
                  onClick={async () => {
                    if (!confirm(`Delete ${it.paper_id}?`)) return;
                    await deleteVFProfile(it.paper_id);
                    await load();
                  }}
                >
                  delete
                </button>
              </div>

              {expanded === it.paper_id && (
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
                  {detailLoading === it.paper_id && <div className="text-sm" style={{ color: "var(--theme-text-muted)" }}>Loading preview...</div>}
                  {CHUNKS.map((chunkId) => {
                    const chunk = detailMap[it.paper_id]?.chunks?.[chunkId] || "";
                    return (
                      <div key={chunkId} className="rounded p-2 text-sm" style={{ border: "1px solid var(--theme-border)" }}>
                        <div className="inline-block text-xs px-2 py-0.5 rounded-full mb-2" style={{ background: "var(--theme-bg)", color: "var(--theme-text-muted)" }}>{chunkId}</div>
                        {chunkId === "meta" ? (
                          <pre className="text-xs overflow-auto">{chunk}</pre>
                        ) : (
                          <div className="prose prose-sm dark:prose-invert max-w-none"><ReactMarkdown>{chunk || "(empty)"}</ReactMarkdown></div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          ))}
          {!loading && filteredItems.length === 0 && <p className="text-sm" style={{ color: "var(--theme-text-muted)" }}>No profiles.</p>}
          {hasMore && (
            <button
              className="w-full rounded px-3 py-2 text-sm"
              style={{ border: "1px solid var(--theme-border)", color: "var(--theme-text-muted)", background: "var(--theme-bg)" }}
              onClick={() => setDisplayLimit((prev) => prev + 20)}
            >
              Show more ({filteredItems.length - displayLimit} remaining)
            </button>
          )}
        </div>
      </div>
    </main>
  );
}
