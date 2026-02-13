"use client";

import React, { useEffect } from "react";
import { useWorkbenchStore } from "@/lib/store";

export function PreferencesPage() {
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
        Appearance
      </h2>

      <div className="space-y-2">
        <label className="flex items-center gap-2 text-sm text-gray-800 dark:text-gray-200">
          <input
            type="radio"
            name="theme"
            value="light"
            checked={theme === "light"}
            onChange={() => setTheme("light")}
          />
          Light
        </label>

        <label className="flex items-center gap-2 text-sm text-gray-800 dark:text-gray-200">
          <input
            type="radio"
            name="theme"
            value="dark"
            checked={theme === "dark"}
            onChange={() => setTheme("dark")}
          />
          Dark
        </label>

        <p className="text-xs text-gray-500 dark:text-gray-400 mt-3">
          This controls the overall UI theme so the workbench doesn’t look half-light / half-dark.
          Dark is the default.
        </p>
      </div>
    </div>
  );
}
