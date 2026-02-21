/**
 * QuickButtons Component
 *
 * Renders configurable quick action buttons for common academic tasks.
 */

"use client";

import React, { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

interface QuickButtonConfig {
  id: string;
  label: string;
  prompt: string;
}

interface QuickButtonsConfig {
  buttons: QuickButtonConfig[];
}

interface QuickButtonsProps {
  onSend: (content: string) => void;
  getSelectedText?: () => string;
  disabled?: boolean;
}

export function QuickButtons({ onSend, getSelectedText, disabled = false }: QuickButtonsProps) {
  const t = useTranslations("quickButtons");
  const localizedFallbackButtons: QuickButtonConfig[] = [
    { id: "cite", label: t("cite.label"), prompt: t("cite.prompt") },
    { id: "harvard", label: t("harvard.label"), prompt: t("harvard.prompt") },
    { id: "summarize", label: t("summarize.label"), prompt: t("summarize.prompt") },
    { id: "improve", label: t("improve.label"), prompt: t("improve.prompt") },
  ];
  const [buttons, setButtons] = useState<QuickButtonConfig[]>(localizedFallbackButtons);

  useEffect(() => {
    let active = true;

    const loadButtons = async () => {
      try {
        const response = await fetch("/quick-buttons.json", { cache: "no-store" });
        if (!response.ok) return;
        const data = (await response.json()) as QuickButtonsConfig;
        if (active && data?.buttons?.length) {
          setButtons(data.buttons);
        }
      } catch {
        // Fall back to defaults silently.
      }
    };

    loadButtons();

    return () => {
      active = false;
    };
  }, []);

  const handleClick = (button: QuickButtonConfig) => {
    if (disabled) return;
    const selection =
      getSelectedText?.() ?? window.getSelection()?.toString().trim() ?? "";
    const content = `${button.prompt}${selection}`.trim();
    if (!content) return;
    onSend(content);
  };

  if (!buttons.length) return null;

  return (
    <div className="mt-3">
      <div className="text-[11px] uppercase tracking-wide text-gray-400 dark:text-gray-500 mb-2">
        {t("title")}
      </div>
      <div className="flex flex-wrap gap-2">
        {buttons.map((button) => (
          <button
            key={button.id}
            type="button"
            onClick={() => handleClick(button)}
            disabled={disabled}
            className={
              "px-3 py-1.5 rounded-full border text-xs font-medium transition-colors " +
              (disabled
                ? "border-gray-200 dark:border-gray-700 text-gray-300 dark:text-gray-500 bg-gray-50 dark:bg-gray-800 cursor-not-allowed"
                : "border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-200 bg-white dark:bg-gray-900 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100")
            }
          >
            {button.label}
          </button>
        ))}
      </div>
    </div>
  );
}
