"use client";

import { useEffect } from "react";
import { useWorkbenchStore } from "@/lib/store";
import { themes, isValidTheme } from "@/lib/themes";

export function ThemeApplier() {
  const theme = useWorkbenchStore((s) => s.theme);
  const setTheme = useWorkbenchStore((s) => s.setTheme);

  // Load from localStorage on first mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("agentb:theme");
      if (isValidTheme(saved)) {
        setTheme(saved);
      } else {
        setTheme("dark");
      }
    } catch {
      // ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Apply theme: Tailwind dark class + CSS custom properties
  useEffect(() => {
    const root = document.documentElement;
    const colors = themes[theme];

    // Tailwind dark mode class
    if (colors.isDark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }

    // data-theme attribute for CSS selectors
    root.setAttribute("data-theme", theme);

    // Inject CSS custom properties
    root.style.setProperty("--theme-bg", colors.bg);
    root.style.setProperty("--theme-bg-secondary", colors.bgSecondary);
    root.style.setProperty("--theme-text", colors.text);
    root.style.setProperty("--theme-text-muted", colors.textMuted);
    root.style.setProperty("--theme-accent", colors.accent);
    root.style.setProperty("--theme-border", colors.border);

    // Persist selection
    try {
      localStorage.setItem("agentb:theme", theme);
    } catch {
      // ignore
    }
  }, [theme]);

  return null;
}
