"use client";

import { useEffect } from "react";
import { useWorkbenchStore } from "@/lib/store";

export function ThemeApplier() {
  const theme = useWorkbenchStore((s) => s.theme);
  const setTheme = useWorkbenchStore((s) => s.setTheme);

  // Load from localStorage on first mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("agentb:theme");
      if (saved === "light" || saved === "dark") {
        setTheme(saved);
      } else {
        // Default preference
        setTheme("dark");
      }
    } catch {
      // ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Apply to <html> so Tailwind dark: works across app
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") root.classList.add("dark");
    else root.classList.remove("dark");
  }, [theme]);

  return null;
}
