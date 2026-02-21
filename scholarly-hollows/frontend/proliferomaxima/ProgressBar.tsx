"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

interface ProgressData {
  phase?: string;
  current?: number;
  total?: number;
  percent?: number;
  status?: string;
  updated_at?: string;
  added?: number;
  already_exists?: number;
  needs_review?: number;
  failed?: number;
  elapsed_seconds?: number;
  message?: string;
}

export function ProliferomaximaProgressBar() {
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const fetchProgress = async () => {
      try {
        const res = await fetch("/api/v1/proliferomaxima/progress");
        if (!res.ok) return;
        const data: ProgressData = await res.json();
        
        setProgress(data);
        
        // Show if running or recently completed
        if (data.status === "running" || data.status === "completed") {
          setIsVisible(true);
          
          // Auto-hide completed after 10 seconds
          if (data.status === "completed") {
            setTimeout(() => setIsVisible(false), 10000);
          }
        } else if (data.status === "idle") {
          setIsVisible(false);
        }
      } catch {
        // Silently ignore errors
      }
    };

    // Initial fetch
    fetchProgress();

    // Poll every 2 seconds
    const intervalId = setInterval(fetchProgress, 2000);

    return () => clearInterval(intervalId);
  }, []);

  if (!isVisible || !progress) return null;

  const isRunning = progress.status === "running";
  const isCompleted = progress.status === "completed";
  const percent = progress.percent ?? 0;

  return (
    <div className="flex items-center gap-2 px-3 py-1 bg-blue-50 dark:bg-blue-900/30 rounded-lg border border-blue-200 dark:border-blue-800">
      {isRunning && (
        <Loader2 className="h-4 w-4 animate-spin text-blue-600 dark:text-blue-400" />
      )}
      
      <div className="flex flex-col min-w-[140px]">
        <div className="flex items-center justify-between text-xs">
          <span className="text-blue-700 dark:text-blue-300 font-medium">
            {isCompleted ? "✓ Complete" : progress.phase || "Proliferomaxima"}
          </span>
          <span className="text-blue-600 dark:text-blue-400">
            {isRunning ? `${percent.toFixed(0)}%` : ""}
          </span>
        </div>
        
        {/* Progress bar */}
        <div className="h-1.5 bg-blue-200 dark:bg-blue-800 rounded-full overflow-hidden mt-1">
          <div
            className={`h-full transition-all duration-300 ${
              isCompleted 
                ? "bg-green-500" 
                : "bg-blue-600 dark:bg-blue-400"
            }`}
            style={{ width: `${isCompleted ? 100 : percent}%` }}
          />
        </div>
        
        {/* Stats line */}
        {(progress.current !== undefined && progress.total !== undefined) && (
          <div className="text-[10px] text-blue-600/70 dark:text-blue-400/70 mt-0.5">
            {isRunning 
              ? `${progress.current}/${progress.total}`
              : `Added: ${progress.added ?? 0} | Exists: ${progress.already_exists ?? 0} | Review: ${progress.needs_review ?? 0}`
            }
          </div>
        )}
      </div>
      
      {/* Dismiss button for completed */}
      {isCompleted && (
        <button
          onClick={() => setIsVisible(false)}
          className="text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-200 text-xs ml-1"
        >
          ✕
        </button>
      )}
    </div>
  );
}
