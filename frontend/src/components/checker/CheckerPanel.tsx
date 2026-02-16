/**
 * CheckerPanel — main panel showing summary, filters, and annotation list.
 */

"use client";

import React, { useMemo, useCallback } from "react";
import { useWorkbenchStore } from "@/lib/store";
import { AnnotationCard } from "./AnnotationCard";
import { CheckerControls } from "./CheckerControls";
import type { CheckerAnnotation } from "@/lib/api/checker";

type FilterType = "all" | "cite" | "own" | "ai" | "flow";

const FILTER_BUTTONS: { key: FilterType; label: string }[] = [
  { key: "all", label: "All" },
  { key: "cite", label: "🔴 Cite" },
  { key: "own", label: "🟡 Own" },
  { key: "ai", label: "🟣 AI" },
  { key: "flow", label: "⚪ Flow" },
];

function matchesFilter(a: CheckerAnnotation, filter: FilterType): boolean {
  switch (filter) {
    case "all": return true;
    case "cite": return a.type === "CITE_NEEDED";
    case "own": return a.type === "OWN_CONTRIBUTION" || a.type === "OWN_EMPIRICAL";
    case "ai": return a.ai_flags.length > 0;
    case "flow": return a.flow.prev === "WEAK" || a.flow.prev === "MISSING";
  }
}

interface CheckerPanelProps {
  /** Callback to get the current editor text */
  getText: () => string;
  /** Current artifact ID */
  artifactId?: string;
}

export function CheckerPanel({ getText, artifactId }: CheckerPanelProps) {
  const {
    checkerResults,
    checkerFilter,
    setCheckerFilter,
    checkerStatus,
    checkerDecisions,
    setCheckerDecision,
    requestCheckerHighlight,
  } = useWorkbenchStore();

  const filtered = useMemo(() => {
    if (!checkerResults?.annotations) return [];
    return checkerResults.annotations.filter((a) => {
      if (checkerDecisions[a.sentence_id]) return false;
      return matchesFilter(a, checkerFilter);
    });
  }, [checkerResults, checkerFilter, checkerDecisions]);

  const summary = checkerResults?.summary;

  const handleAccept = useCallback((id: number) => {
    setCheckerDecision(id, "accepted");
  }, [setCheckerDecision]);

  const handleDismiss = useCallback((id: number) => {
    setCheckerDecision(id, "dismissed");
  }, [setCheckerDecision]);

  const handleHighlight = useCallback((annotation: CheckerAnnotation) => {
    const comment = [
      `VF ${annotation.type} (${annotation.confidence})`,
      annotation.reasoning?.trim() || "No reasoning provided.",
    ].join(" — ");

    requestCheckerHighlight({
      sentenceId: annotation.sentence_id,
      sentenceText: annotation.text,
      comment,
      artifactId,
    });
  }, [requestCheckerHighlight, artifactId]);

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      {/* Header */}
      <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <CheckerControls getText={getText} artifactId={artifactId} />
      </div>

      {/* Summary */}
      {summary && (
        <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50">
          <div className="flex items-center gap-3 text-xs flex-wrap">
            <span className="font-medium">{summary.total_sentences} sentences</span>
            <span className="text-red-600">{summary.cite_needed} 🔴</span>
            <span className="text-green-600">{summary.common} ✅</span>
            <span className="text-blue-600">{summary.own_empirical} 🔵</span>
            <span className="text-yellow-600">{summary.own_contribution} 🟡</span>
            {summary.ai_patterns > 0 && (
              <span className="text-purple-600">{summary.ai_patterns} 🟣</span>
            )}
            {summary.flow_issues > 0 && (
              <span className="text-gray-500">{summary.flow_issues} ⚪</span>
            )}
          </div>
        </div>
      )}

      {/* Filter bar */}
      {checkerResults && (
        <div className="px-3 py-1.5 border-b border-gray-200 dark:border-gray-700 flex gap-1 flex-wrap">
          {FILTER_BUTTONS.map((btn) => (
            <button
              key={btn.key}
              onClick={() => setCheckerFilter(btn.key)}
              className={`px-2 py-0.5 text-xs rounded transition-colors ${
                checkerFilter === btn.key
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              }`}
            >
              {btn.label}
            </button>
          ))}
        </div>
      )}

      {/* Annotation list */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
        {checkerStatus === "idle" && !checkerResults && (
          <div className="text-center text-sm text-gray-400 dark:text-gray-500 py-12">
            Click &ldquo;🪄 Cast Veritafactum&rdquo; to analyse the current artifact.
          </div>
        )}

        {checkerStatus === "completed" && filtered.length === 0 && (
          <div className="text-center text-sm text-gray-400 dark:text-gray-500 py-8">
            No annotations match the current filter.
          </div>
        )}

        {filtered.map((annotation) => (
          <AnnotationCard
            key={annotation.sentence_id}
            annotation={annotation}
            index={annotation.sentence_id}
            state={checkerDecisions[annotation.sentence_id]}
            onAccept={handleAccept}
            onDismiss={handleDismiss}
            onHighlight={handleHighlight}
          />
        ))}
      </div>
    </div>
  );
}
