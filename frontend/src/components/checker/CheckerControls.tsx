/**
 * CheckerControls — run button, progress bar, and option checkboxes.
 */

"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import { Wand2, Loader2, AlertCircle, Sparkles } from "lucide-react";
import { useWorkbenchStore } from "@/lib/store";
import { startCheckerRun, getCheckerStatus, getCheckerResults } from "@/lib/api/checker";
import type { CheckerRunOptions } from "@/lib/api/checker";

interface CheckerControlsProps {
  /** The plain text to check */
  getText: () => string;
  /** Current artifact ID (optional) */
  artifactId?: string;
}

export function CheckerControls({ getText, artifactId }: CheckerControlsProps) {
  const {
    checkerStatus,
    setCheckerRunId,
    setCheckerStatus,
    setCheckerResults,
  } = useWorkbenchStore();

  const [options, setOptions] = useState<CheckerRunOptions>({
    check_citations: true,
    check_ai: true,
    check_flow: true,
  });

  const [progress, setProgress] = useState<{ current: number; total: number; step: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // Poll for status when running
  const startPolling = useCallback((runId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);

    pollRef.current = setInterval(async () => {
      try {
        const status = await getCheckerStatus(runId);
        if (status.progress) setProgress(status.progress);

        if (status.status === "completed") {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          setCheckerStatus("completed");

          // Fetch full results
          const res = await getCheckerResults(runId);
          if (res.results) {
            setCheckerResults(res.results);
          }
        } else if (status.status === "failed") {
          clearInterval(pollRef.current!);
          pollRef.current = null;
          setCheckerStatus("error");
          setError(status.error || "Spell failed");
        }
      } catch (err) {
        // Keep polling on transient errors
        console.error("Checker poll error:", err);
      }
    }, 2000);
  }, [setCheckerStatus, setCheckerResults]);

  const handleRun = async () => {
    const text = getText();
    if (!text.trim()) {
      setError("No text to check");
      return;
    }

    setError(null);
    setProgress(null);
    setCheckerStatus("running");

    try {
      const res = await startCheckerRun(text, artifactId, options);
      setCheckerRunId(res.run_id);
      startPolling(res.run_id);
    } catch (err) {
      setCheckerStatus("error");
      setError(err instanceof Error ? err.message : "Failed to cast spell");
    }
  };

  const isRunning = checkerStatus === "running";
  const progressPct = progress && progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : 0;

  return (
    <div className="space-y-2">
      {/* Run button + options */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={handleRun}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isRunning ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Casting spell…
            </>
          ) : (
            <>
              <Wand2 className="h-4 w-4" />
              🪄 Cast Veritafactum
            </>
          )}
        </button>

        {/* Option checkboxes */}
        <label className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={options.check_citations}
            onChange={(e) => setOptions((o) => ({ ...o, check_citations: e.target.checked }))}
            className="rounded"
          />
          Citations
        </label>
        <label className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={options.check_ai}
            onChange={(e) => setOptions((o) => ({ ...o, check_ai: e.target.checked }))}
            className="rounded"
          />
          AI Detect
        </label>
        <label className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-400 cursor-pointer">
          <input
            type="checkbox"
            checked={options.check_flow}
            onChange={(e) => setOptions((o) => ({ ...o, check_flow: e.target.checked }))}
            className="rounded"
          />
          Flow
        </label>
      </div>

      {/* Progress bar */}
      {isRunning && progress && (
        <div className="space-y-1">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>{progress.step || "Processing…"}</span>
            <span>{progress.current}/{progress.total} ({progressPct}%)</span>
          </div>
          <div className="w-full h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-1.5 text-xs text-red-600 dark:text-red-400">
          <AlertCircle className="h-3.5 w-3.5" />
          {error}
        </div>
      )}
    </div>
  );
}
