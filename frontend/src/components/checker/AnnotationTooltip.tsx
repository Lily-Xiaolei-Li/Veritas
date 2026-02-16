/**
 * AnnotationTooltip — hover tooltip for highlighted sentences in the editor.
 */

"use client";

import React from "react";
import type { CheckerAnnotation } from "@/lib/api/checker";

const TYPE_LABELS: Record<string, string> = {
  CITE_NEEDED: "🔴 Citation Needed",
  COMMON: "✅ Common Knowledge",
  OWN_EMPIRICAL: "🔵 Own Empirical",
  OWN_CONTRIBUTION: "🟡 Own Contribution",
};

interface AnnotationTooltipProps {
  annotation: CheckerAnnotation;
  x: number;
  y: number;
}

export function AnnotationTooltip({ annotation, x, y }: AnnotationTooltipProps) {
  const label = TYPE_LABELS[annotation.type] || annotation.type;
  const hasAI = annotation.ai_flags.length > 0;
  const hasFlow = annotation.flow.prev === "WEAK" || annotation.flow.prev === "MISSING";

  return (
    <div
      className="fixed z-[9999] max-w-xs bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 p-3 text-sm pointer-events-none"
      style={{ left: x, top: y + 8 }}
    >
      <div className="font-semibold mb-1">{label}</div>
      <div className="text-gray-500 dark:text-gray-400 text-xs mb-1">
        Confidence: {annotation.confidence}
      </div>
      {annotation.reasoning && (
        <div className="text-gray-700 dark:text-gray-300 text-xs line-clamp-2">
          {annotation.reasoning}
        </div>
      )}
      {hasAI && (
        <div className="mt-1 text-purple-600 dark:text-purple-400 text-xs">
          🟣 AI pattern detected
        </div>
      )}
      {hasFlow && (
        <div className="mt-1 text-gray-500 text-xs">
          ⚪ Flow issue: {annotation.flow.prev} transition
        </div>
      )}
      {annotation.suggested_citations.length > 0 && (
        <div className="mt-1 text-xs text-blue-600 dark:text-blue-400">
          💡 {annotation.suggested_citations[0].ref}
        </div>
      )}
    </div>
  );
}
