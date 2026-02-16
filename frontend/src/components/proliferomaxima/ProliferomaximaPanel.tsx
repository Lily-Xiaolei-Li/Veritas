"use client";

import React, { useRef, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import {
  getProliferomaximaResults,
  getProliferomaximaStatus,
  startProliferomaximaRun,
  type ProliferomaximaSummary,
} from "@/lib/api/proliferomaxima";

export function ProliferomaximaPanel({ onClose }: { onClose: () => void }) {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "running" | "completed" | "error">("idle");
  const [progress, setProgress] = useState<{ current: number; total: number; step: string } | null>(null);
  const [results, setResults] = useState<ProliferomaximaSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [maxFiles, setMaxFiles] = useState<number>(20);
  const [maxItems, setMaxItems] = useState<number>(300);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const start = async () => {
    setError(null);
    setResults(null);
    setStatus("running");
    const run = await startProliferomaximaRun({
      max_files: maxFiles > 0 ? maxFiles : undefined,
      max_items: maxItems > 0 ? maxItems : undefined,
    });
    setRunId(run.run_id);

    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const s = await getProliferomaximaStatus(run.run_id);
        if (s.progress) setProgress(s.progress);
        if (s.status === "completed") {
          clearInterval(pollRef.current!);
          const r = await getProliferomaximaResults(run.run_id);
          setResults(r.results);
          setStatus("completed");
        } else if (s.status === "failed") {
          clearInterval(pollRef.current!);
          setStatus("error");
          setError(s.error || "Proliferomaxima failed");
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold">✨ Proliferomaxima</h3>
          <button onClick={onClose} className="text-sm text-gray-500">Close</button>
        </div>

        <div className="p-4 space-y-3">
          <p className="text-sm text-gray-600 dark:text-gray-300">从 library references 批量生成 abstract-only VF profiles。</p>

          <div className="grid grid-cols-2 gap-3 text-sm">
            <label className="flex flex-col gap-1">
              Max files
              <input type="number" value={maxFiles} onChange={(e) => setMaxFiles(Number(e.target.value || 0))} className="border rounded px-2 py-1 dark:bg-gray-700" />
            </label>
            <label className="flex flex-col gap-1">
              Max refs
              <input type="number" value={maxItems} onChange={(e) => setMaxItems(Number(e.target.value || 0))} className="border rounded px-2 py-1 dark:bg-gray-700" />
            </label>
          </div>

          <button
            onClick={start}
            disabled={status === "running"}
            className="px-3 py-1.5 rounded bg-purple-600 text-white text-sm hover:bg-purple-700 disabled:opacity-60 inline-flex items-center gap-2"
          >
            {status === "running" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} Start spell
          </button>

          {runId && <div className="text-xs text-gray-500">run_id: {runId}</div>}
          {progress && <div className="text-xs text-gray-500">{progress.step} {progress.current}/{progress.total}</div>}
          {error && <div className="text-xs text-red-500">{error}</div>}

          {results && (
            <div className="text-sm border rounded p-3 space-y-1 bg-gray-50 dark:bg-gray-900/40">
              <div>added: <b>{results.added}</b></div>
              <div>skipped: {results.skipped}</div>
              <div>duplicates: {results.duplicates}</div>
              <div>failed: {results.failed}</div>
              <div>total refs: {results.total_refs}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
