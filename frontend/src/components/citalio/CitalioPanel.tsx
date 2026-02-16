"use client";

import React, { useMemo, useRef, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { getCitalioResults, getCitalioStatus, startCitalioRun, type CitalioResults, type CitalioSentenceResult } from "@/lib/api/citalio";

type Props = {
  getText: () => string;
  artifactId?: string;
  onApplyAll?: (updatedText: string) => void;
};

const ACTION_STYLE: Record<string, string> = {
  auto_cite: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  maybe_cite: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
  manual_needed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  no_cite_needed: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
};

export function CitalioPanel({ getText, onApplyAll }: Props) {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "running" | "completed" | "error">("idle");
  const [progress, setProgress] = useState<{ current: number; total: number; step: string } | null>(null);
  const [results, setResults] = useState<CitalioResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedBySentence, setSelectedBySentence] = useState<Record<number, number>>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const sentenceById = useMemo(() => {
    const m: Record<number, CitalioSentenceResult> = {};
    for (const s of results?.sentences || []) m[s.sentence_id] = s;
    return m;
  }, [results]);

  const applyAll = () => {
    if (!results) return;
    const merged = (results.sentences || []).map((s) => {
      if (s.action === "manual_needed" || s.action === "no_cite_needed") return s.text;
      const chosen = selectedBySentence[s.sentence_id] ?? 0;
      const candidate = s.candidates[chosen];
      if (!candidate) return s.text;
      const clean = s.text.replace(/[.!?]\s*$/, "");
      const punct = /[.!?]\s*$/.test(s.text) ? s.text.match(/[.!?]\s*$/)?.[0].trim() || "." : ".";
      return `${clean} ${candidate.citation_text}${punct}`;
    });
    onApplyAll?.(merged.join(" "));
  };

  const start = async () => {
    const text = getText();
    if (!text.trim()) {
      setError("No text to analyze");
      return;
    }
    setError(null);
    setResults(null);
    setStatus("running");
    const run = await startCitalioRun({ text, options: { min_confidence: 0.5, max_citations_per_sentence: 3 } });
    setRunId(run.run_id);

    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const s = await getCitalioStatus(run.run_id);
        if (s.progress) setProgress(s.progress);
        if (s.status === "completed") {
          clearInterval(pollRef.current!);
          const r = await getCitalioResults(run.run_id);
          setResults(r.results);
          setStatus("completed");
        } else if (s.status === "failed") {
          clearInterval(pollRef.current!);
          setStatus("error");
          setError(s.error || "Citalio failed");
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
  };

  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
        <button
          onClick={start}
          disabled={status === "running"}
          className="px-3 py-1.5 rounded bg-purple-600 text-white text-sm hover:bg-purple-700 disabled:opacity-60 inline-flex items-center gap-2"
        >
          {status === "running" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} ✨ Citalio
        </button>
        <button onClick={applyAll} disabled={!results} className="px-3 py-1.5 rounded bg-green-600 text-white text-sm hover:bg-green-700 disabled:opacity-50">一键全部接受</button>
        {runId && <span className="text-xs text-gray-500">{runId}</span>}
      </div>

      {status === "running" && progress && (
        <div className="px-3 py-2 text-xs text-gray-500 border-b border-gray-200 dark:border-gray-700">
          {progress.step} {progress.current}/{progress.total}
        </div>
      )}
      {error && <div className="px-3 py-2 text-xs text-red-500">{error}</div>}

      {results && (
        <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 text-xs flex gap-3 flex-wrap">
          <span>total {results.summary.total_sentences}</span>
          <span className="text-green-600">auto {results.summary.auto_cited}</span>
          <span className="text-yellow-600">maybe {results.summary.maybe_cited}</span>
          <span className="text-red-600">manual {results.summary.manual_needed}</span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {(results?.sentences || []).map((s) => (
          <div key={s.id} className="border border-gray-200 dark:border-gray-700 rounded">
            <div className="px-2 py-1 text-xs flex items-center gap-2 border-b border-gray-200 dark:border-gray-700">
              <span className={`px-1.5 py-0.5 rounded ${ACTION_STYLE[s.action] || ACTION_STYLE.no_cite_needed}`}>{s.action}</span>
              <span className="text-gray-500">{s.classification}</span>
            </div>
            <div className="p-2 text-sm">{s.text}</div>
            {s.candidates.length > 0 && (
              <div className="px-2 pb-2">
                <div className="text-xs text-gray-500 mb-1">候选引用</div>
                <div className="space-y-1">
                  {s.candidates.map((c, i) => (
                    <label key={`${s.id}-${c.paper_id}-${i}`} className="text-xs flex items-start gap-2 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                      <input
                        type="radio"
                        name={`citalio-${s.id}`}
                        checked={(selectedBySentence[s.sentence_id] ?? 0) === i}
                        onChange={() => setSelectedBySentence((prev) => ({ ...prev, [s.sentence_id]: i }))}
                      />
                      <span className="flex-1">
                        <span className="font-medium">{c.citation_text}</span> — {c.title}
                        <span className="text-gray-500"> ({Math.round(c.confidence * 100)}%)</span>
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
