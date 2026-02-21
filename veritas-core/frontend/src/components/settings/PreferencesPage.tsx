"use client";

import React, { useEffect } from "react";
import { useWorkbenchStore } from "@/lib/store";
import { useTranslations } from "next-intl";
import { themes, THEME_NAMES, type ThemeName } from "@/lib/themes";

export function PreferencesPage() {
  const t = useTranslations();
  const theme = useWorkbenchStore((s) => s.theme);
  const setTheme = useWorkbenchStore((s) => s.setTheme);

  // Persist to localStorage
  useEffect(() => {
    try {
      localStorage.setItem("agentb:theme", theme);
    } catch {
      // ignore
    }
  }, [theme]);

  return (
    <div className="p-6">
      <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4">
        {t("settings.appearance")}
      </h2>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {THEME_NAMES.map((name) => (
          <ThemeCard
            key={name}
            name={name}
            selected={theme === name}
            onSelect={() => setTheme(name)}
          />
        ))}
      </div>

      <p className="text-xs text-gray-500 dark:text-gray-400 mt-4">
        {t("settings.themeHint")}
      </p>
    </div>
  );
}

function ThemeCard({
  name,
  selected,
  onSelect,
}: {
  name: ThemeName;
  selected: boolean;
  onSelect: () => void;
}) {
  const t = themes[name];

  return (
    <button
      onClick={onSelect}
      className={`
        relative rounded-lg p-3 text-left transition-all cursor-pointer
        border-2
        ${selected
          ? "border-blue-500 ring-2 ring-blue-500/30"
          : "border-gray-200 dark:border-gray-700 hover:border-gray-400 dark:hover:border-gray-500"
        }
      `}
      style={{ backgroundColor: t.bg }}
    >
      {/* Color swatches */}
      <div className="flex gap-1.5 mb-2">
        {t.swatches.map((color, i) => (
          <div
            key={i}
            className="w-5 h-5 rounded-full border border-white/20"
            style={{ backgroundColor: color }}
          />
        ))}
      </div>

      {/* Theme name */}
      <div
        className="text-xs font-medium leading-tight whitespace-normal"
        style={{ color: t.text }}
      >
        {name === "catppuccin" ? "Catpp" : t.label}
      </div>

      {/* Selected indicator */}
      {selected && (
        <div className="absolute top-1.5 right-1.5 w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center">
          <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
      )}
    </button>
  );
}
