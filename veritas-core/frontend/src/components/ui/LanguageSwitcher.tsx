"use client";

import { Languages } from "lucide-react";
import { useTranslations } from "next-intl";
import { useWorkbenchStore } from "@/lib/store";

export function LanguageSwitcher() {
  const t = useTranslations("language");
  const locale = useWorkbenchStore((s) => s.locale);
  const setLocale = useWorkbenchStore((s) => s.setLocale);

  const toggle = () => {
    const nextLocale = locale === "en" ? "zh" : "en";
    setLocale(nextLocale);
    try {
      localStorage.setItem("agentb:locale", nextLocale);
    } catch {
      // ignore
    }
  };

  return (
    <button
      onClick={toggle}
      className="inline-flex items-center gap-1.5 px-2 py-1 text-xs rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800"
      aria-label={t("switchTo")}
      title={t("switchTo")}
    >
      <Languages className="h-3.5 w-3.5" />
      <span>{locale === "en" ? t("en") : t("zh")}</span>
    </button>
  );
}
