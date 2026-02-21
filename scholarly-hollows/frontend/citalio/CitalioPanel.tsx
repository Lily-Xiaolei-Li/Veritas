"use client";

import React, { useRef, useState } from "react";
import { Loader2, Sparkles, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { getCitalioResults, getCitalioStatus, startCitalioRun, type CitalioResults } from "@/lib/api/citalio";
import { CitalioManualPanel } from "./CitalioManualPanel";

type Props = {
  getText: () => string;
  artifactId?: string;
  onApplyAll?: (updatedText: string) => void;
  selectedText?: string;
  onInsertCitation?: (intext: string, fullRef: string, position?: "end" | "cursor") => void;
};

type Mode = "auto" | "manual";

const ACTION_STYLE: Record<string, string> = {
  auto_cite: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300",
  maybe_cite: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300",
  manual_needed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
  no_cite_needed: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300",
};

export function CitalioPanel({ getText, onApplyAll, selectedText = "", onInsertCitation }: Props) {
  const t = useTranslations("citalio");
  const [mode, setMode] = useState<Mode>("manual"); // Default to manual mode
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "running" | "completed" | "error">("idle");
  const [progress, setProgress] = useState<{ current: number; total: number; step: string } | null>(null);
  const [results, setResults] = useState<CitalioResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedBySentence, setSelectedBySentence] = useState<Record<number, number>>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const actionLabel = (action: string) => {
    const keyMap: Record<string, string> = {
      auto_cite: "autoCite",
      maybe_cite: "maybeCite",
      manual_needed: "manualNeeded",
      no_cite_needed: "noCiteNeeded",
    };
    return t(keyMap[action] || "noCiteNeeded");
  };

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
      setError(t("noText"));
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
          setError(s.error || t("failed"));
        }
      } catch (e) {
        console.error(e);
      }
    }, 2000);
  };

  // Handler for manual mode citation insertion
  const handleManualInsert = (intext: string, fullRef: string) => {
    if (onInsertCitation) {
      onInsertCitation(intext, fullRef, "end");
    } else if (onApplyAll) {
      // Fallback: append to end of text with reference
      const currentText = getText();
      const hasReferences = currentText.toLowerCase().includes("## references") || 
                           currentText.toLowerCase().includes("# references");
      
      let newText = currentText;
      
      // If no REFERENCES section, add one
      if (!hasReferences) {
        newText = currentText.trimEnd() + "\n\n## REFERENCES\n\n" + fullRef;
      } else {
        // Append to existing REFERENCES section
        newText = currentText.trimEnd() + "\n" + fullRef;
      }
      
      onApplyAll(newText);
    }
  };

  // Manual mode panel
  if (mode === "manual") {
    return (
      <div className="h-full flex flex-col bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
        {/* Mode Toggle Header */}
        <div className="p-2 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
          <button
            onClick={() => setMode("auto")}
            className="px-3 py-1 text-xs rounded bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
          >
            <Sparkles className="h-3 w-3 inline mr-1" />
            Auto
          </button>
          <button
            onClick={() => setMode("manual")}
            className="px-3 py-1 text-xs rounded bg-purple-600 text-white"
          >
            <Search className="h-3 w-3 inline mr-1" />
            Manual
          </button>
        </div>
        
        {/* Manual Panel */}
        <div className="flex-1 overflow-hidden">
          <CitalioManualPanel
            selectedText={selectedText || ""}
            onInsertCitation={handleManualInsert}
          />
        </div>
      </div>
    );
  }

  // Auto mode panel (original)
  return (
    <div className="h-full flex flex-col bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      {/* Mode Toggle Header */}
      <div className="p-2 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
        <button
          onClick={() => setMode("auto")}
          className="px-3 py-1 text-xs rounded bg-purple-600 text-white"
        >
          <Sparkles className="h-3 w-3 inline mr-1" />
          Auto
        </button>
        <button
          onClick={() => setMode("manual")}
          className="px-3 py-1 text-xs rounded bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700"
        >
          <Search className="h-3 w-3 inline mr-1" />
          Manual
        </button>
      </div>

      {/* Auto Mode Content */}
      <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center gap-2">
        <button onClick={start} disabled={status === "running"} className="px-3 py-1.5 rounded bg-purple-600 text-white text-sm hover:bg-purple-700 disabled:opacity-60 inline-flex items-center gap-2">
          {status === "running" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} ✨ {t("title")}
        </button>
        <button onClick={applyAll} disabled={!results} className="px-3 py-1.5 rounded bg-green-600 text-white text-sm hover:bg-green-700 disabled:opacity-50">{t("acceptAll")}</button>
        {runId && <span className="text-xs text-gray-500">{runId}</span>}
      </div>

      {status === "running" && progress && <div className="px-3 py-2 text-xs text-gray-500 border-b border-gray-200 dark:border-gray-700">{progress.step} {progress.current}/{progress.total}</div>}
      {error && <div className="px-3 py-2 text-xs text-red-500">{error}</div>}

      {results && (
        <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 text-xs flex gap-3 flex-wrap">
          <span>{t("summary.total", { count: results.summary.total_sentences })}</span>
          <span className="text-green-600">{t("summary.auto", { count: results.summary.auto_cited })}</span>
          <span className="text-yellow-600">{t("summary.maybe", { count: results.summary.maybe_cited })}</span>
          <span className="text-red-600">{t("summary.manual", { count: results.summary.manual_needed })}</span>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {(results?.sentences || []).map((s) => (
          <div key={s.id} className="border border-gray-200 dark:border-gray-700 rounded">
            <div className="px-2 py-1 text-xs flex items-center gap-2 border-b border-gray-200 dark:border-gray-700">
              <span className={`px-1.5 py-0.5 rounded ${ACTION_STYLE[s.action] || ACTION_STYLE.no_cite_needed}`}>{actionLabel(s.action)}</span>
              <span className="text-gray-500">{s.classification}</span>
            </div>
            <div className="p-2 text-sm">{s.text}</div>
            {s.candidates.length > 0 && (
              <div className="px-2 pb-2">
                <div className="text-xs text-gray-500 mb-1">{t("candidates")}</div>
                <div className="space-y-1">
                  {s.candidates.map((c, i) => (
                    <label key={`${s.id}-${c.paper_id}-${i}`} className="text-xs flex items-start gap-2 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800">
                      <input type="radio" name={`citalio-${s.id}`} checked={(selectedBySentence[s.sentence_id] ?? 0) === i} onChange={() => setSelectedBySentence((prev) => ({ ...prev, [s.sentence_id]: i }))} />
                      <span className="flex-1"><span className="font-medium">{c.citation_text}</span> — {c.title}<span className="text-gray-500"> ({Math.round(c.confidence * 100)}%)</span></span>
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
