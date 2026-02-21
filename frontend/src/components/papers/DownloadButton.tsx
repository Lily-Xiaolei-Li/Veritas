"use client";

/**
 * Download PDF Button — shown next to search results.
 * Triggers single paper download via DOI.
 */

import React, { useState } from "react";
import { Download, Check, X, Loader2 } from "lucide-react";
import { downloadPaper, SingleDownloadResponse } from "@/lib/api/papers";

interface DownloadButtonProps {
  doi?: string;
  title?: string;
  className?: string;
  compact?: boolean;
}

export function DownloadButton({ doi, title, className = "", compact = false }: DownloadButtonProps) {
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [result, setResult] = useState<SingleDownloadResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState("");

  const handleDownload = async () => {
    if (!doi && !title) return;
    setStatus("loading");
    setErrorMsg("");

    try {
      const res = await downloadPaper({ doi, title, use_ezproxy: true });
      setResult(res);
      if (res.status === "success") {
        setStatus("success");
      } else {
        setStatus("error");
        setErrorMsg(res.error || res.status);
      }
    } catch (e: unknown) {
      setStatus("error");
      setErrorMsg((e as Error)?.message || "Download failed");
    }
  };

  const icon = {
    idle: <Download className="w-4 h-4" />,
    loading: <Loader2 className="w-4 h-4 animate-spin" />,
    success: <Check className="w-4 h-4 text-green-500" />,
    error: <X className="w-4 h-4 text-red-500" />,
  }[status];

  const label = compact ? "" : {
    idle: "PDF",
    loading: "Downloading...",
    success: "Downloaded",
    error: "Failed",
  }[status];

  return (
    <div className="inline-flex items-center gap-1">
      <button
        onClick={handleDownload}
        disabled={status === "loading" || (!doi && !title)}
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md
          transition-colors duration-200
          ${status === "success"
            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
            : status === "error"
            ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
            : "bg-blue-100 text-blue-700 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/50"
          }
          disabled:opacity-50 disabled:cursor-not-allowed
          ${className}`}
        title={errorMsg || (result?.file_path ? `Saved: ${result.file_path}` : "Download PDF")}
      >
        {icon}
        {label && <span>{label}</span>}
      </button>
      {result?.file_size ? (
        <span className="text-[10px] text-gray-400">
          {(result.file_size / 1024 / 1024).toFixed(1)}MB
        </span>
      ) : null}
    </div>
  );
}
