"use client";

import React, { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { useTranslations } from "next-intl";

type Props = {
  score: number;
  breakdown?: Record<string, unknown> | null;
};

function getLevel(score: number) {
  if (score < 0.3) return { label: "Low", bg: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300", dot: "bg-red-500" };
  if (score < 0.6) return { label: "Medium", bg: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300", dot: "bg-yellow-500" };
  return { label: "High", bg: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300", dot: "bg-green-500" };
}

export function CredibilityBadge({ score, breakdown }: Props) {
  const t = useTranslations("gnosiplexio");
  const [showTooltip, setShowTooltip] = useState(false);
  const { label, bg, dot } = getLevel(score);
  const localizedLabel =
    label === "Low" ? t("credibility.low") : label === "Medium" ? t("credibility.medium") : t("credibility.high");

  return (
    <div className="relative inline-block">
      <button
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${bg} cursor-pointer`}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <span className={`w-2 h-2 rounded-full ${dot}`} />
        <ShieldCheck className="w-3 h-3" />
        {localizedLabel} ({(score * 100).toFixed(0)}%)
      </button>
      {showTooltip && breakdown && (
        <div className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 p-3 rounded-lg shadow-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-xs">
          <p className="font-semibold mb-1">{t("credibility.breakdown")}</p>
          {Object.entries(breakdown).map(([k, v]) => (
            <div key={k} className="flex justify-between py-0.5">
              <span className="text-gray-500 dark:text-gray-400">{k}</span>
              <span className="font-mono">{String(v)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
