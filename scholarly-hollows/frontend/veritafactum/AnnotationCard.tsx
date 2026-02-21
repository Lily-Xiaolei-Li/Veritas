/**
 * AnnotationCard — single annotation card in the CheckerPanel.
 */

"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronUp, Check, X, Highlighter } from "lucide-react";
import { useTranslations } from "next-intl";
import type { CheckerAnnotation } from "@/lib/api/checker";

interface AnnotationCardProps {
  annotation: CheckerAnnotation;
  index: number;
  state?: "accepted" | "dismissed";
  onAccept?: (id: number) => void;
  onDismiss?: (id: number) => void;
  onHighlight?: (annotation: CheckerAnnotation) => void;
}

export function AnnotationCard({ annotation, index, state, onAccept, onDismiss, onHighlight }: AnnotationCardProps) {
  const t = useTranslations("checker");
  const [expanded, setExpanded] = useState(false);

  const typeStyles: Record<string, { bg: string; text: string; label: string }> = {
    CITE_NEEDED: { bg: "bg-red-100 dark:bg-red-900/30", text: "text-red-700 dark:text-red-300", label: t("type.cite") },
    COMMON: { bg: "bg-green-100 dark:bg-green-900/30", text: "text-green-700 dark:text-green-300", label: t("type.common") },
    OWN_EMPIRICAL: { bg: "bg-blue-100 dark:bg-blue-900/30", text: "text-blue-700 dark:text-blue-300", label: t("type.ownData") },
    OWN_CONTRIBUTION: { bg: "bg-yellow-100 dark:bg-yellow-900/30", text: "text-yellow-700 dark:text-yellow-300", label: t("type.ownArg") },
  };

  const style = typeStyles[annotation.type] || typeStyles.COMMON;
  const truncatedText = annotation.text.length > 80 ? annotation.text.slice(0, 80) + "…" : annotation.text;
  const isHandled = !!state;

  return (
    <div className={`rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden transition-all ${style.bg} ${isHandled ? "opacity-50" : ""}`}>
      <button onClick={() => setExpanded(!expanded)} className="w-full flex items-start gap-2 px-3 py-2 text-left hover:bg-black/5 dark:hover:bg-white/5 transition-colors">
        <span className="text-xs font-mono text-gray-400 mt-0.5">#{index + 1}</span>
        <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${style.text} whitespace-nowrap`}>{style.label}</span>
        <span className="text-xs text-gray-700 dark:text-gray-300 flex-1 line-clamp-1">{truncatedText}</span>
        <span className="text-xs text-gray-400">{annotation.confidence}</span>
        {expanded ? <ChevronUp className="h-3.5 w-3.5 text-gray-400 flex-shrink-0 mt-0.5" /> : <ChevronDown className="h-3.5 w-3.5 text-gray-400 flex-shrink-0 mt-0.5" />}
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-gray-200/50 dark:border-gray-700/50">
          <p className="text-xs text-gray-600 dark:text-gray-400 italic mt-2">&ldquo;{annotation.text}&rdquo;</p>

          {annotation.reasoning && (
            <div className="text-xs text-gray-700 dark:text-gray-300">
              <span className="font-semibold">{t("reasoning")}:</span> {annotation.reasoning}
            </div>
          )}

          {annotation.suggested_citations.length > 0 && (
            <div className="text-xs">
              <span className="font-semibold text-gray-700 dark:text-gray-300">{t("suggested")}:</span>
              <ul className="mt-1 space-y-0.5">
                {annotation.suggested_citations.map((c, i) => (
                  <li key={i} className="text-blue-600 dark:text-blue-400 ml-3">
                    📎 {c.ref}
                    {c.snippet && <span className="text-gray-500 ml-1 italic">&mdash; &ldquo;{c.snippet}&rdquo;</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {annotation.existing_citations_status.length > 0 && (
            <div className="text-xs">
              <span className="font-semibold text-gray-700 dark:text-gray-300">{t("citations")}:</span>
              <ul className="mt-1 space-y-0.5 ml-3">
                {annotation.existing_citations_status.map((v, i) => (
                  <li key={i}>{v.status === "VERIFIED" ? "✅" : v.status === "MISATTRIBUTED" ? "🟠" : "❓"} {v.citation}: {v.note}</li>
                ))}
              </ul>
            </div>
          )}

          {annotation.ai_flags.length > 0 && (
            <div className="text-xs">
              {annotation.ai_flags.map((f, i) => (
                <div key={i} className="text-purple-600 dark:text-purple-400">🟣 <span className="font-mono">{f.pattern}</span>: {f.note}</div>
              ))}
            </div>
          )}

          {(annotation.flow.prev === "WEAK" || annotation.flow.prev === "MISSING") && (
            <div className="text-xs text-gray-500">
              ⚪ {t("flow")}: {annotation.flow.prev} {t("transition")}
              {annotation.flow.suggestion && <span className="ml-1">— {annotation.flow.suggestion}</span>}
            </div>
          )}

          <div className="flex items-center gap-2 pt-1">
            <button onClick={() => onAccept?.(annotation.sentence_id)} disabled={isHandled} className="flex items-center gap-1 px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"><Check className="h-3 w-3" /> {t("accept")}</button>
            <button onClick={() => onDismiss?.(annotation.sentence_id)} disabled={isHandled} className="flex items-center gap-1 px-2 py-1 text-xs bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"><X className="h-3 w-3" /> {t("dismiss")}</button>
            <button onClick={() => onHighlight?.(annotation)} className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"><Highlighter className="h-3 w-3" /> {t("highlight")}</button>
          </div>
        </div>
      )}
    </div>
  );
}
