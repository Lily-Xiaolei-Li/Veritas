"use client";

/**
 * Batch Import Panel — drag-and-drop CSV/BibTeX upload with progress tracking.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { Upload, Loader2, CheckCircle2, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { importCsv, getBatchStatus, BatchStatusResponse } from "@/lib/api/papers";

export function BatchImport() {
  const t = useTranslations("batchImport");
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [batchStatus, setBatchStatus] = useState<BatchStatusResponse | null>(null);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Poll for batch progress
  useEffect(() => {
    if (!jobId) return;

    const poll = async () => {
      try {
        const status = await getBatchStatus(jobId);
        setBatchStatus(status);
        if (status.status === "completed") {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      } catch {
        // ignore poll errors
      }
    };

    poll();
    pollRef.current = setInterval(poll, 3000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [jobId]);

  const handleFile = useCallback(async (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["csv", "bib", "bibtex", "txt"].includes(ext || "")) {
      setError(t("invalidFileType"));
      return;
    }

    setUploading(true);
    setError("");
    setJobId(null);
    setBatchStatus(null);

    try {
      const result = await importCsv(file);
      setJobId(result.job_id);
    } catch (e: unknown) {
      setError((e as Error)?.message || "Import failed");
    } finally {
      setUploading(false);
    }
  }, [t]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const onFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const progressPercent = batchStatus
    ? Math.round((batchStatus.completed / Math.max(batchStatus.total, 1)) * 100)
    : 0;

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
          transition-colors duration-200
          ${dragOver
            ? "border-blue-400 bg-blue-50 dark:bg-blue-900/20"
            : "border-gray-300 dark:border-gray-600 hover:border-blue-300 hover:bg-gray-50 dark:hover:bg-gray-800/50"
          }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.bib,.bibtex,.txt"
          onChange={onFileSelect}
          className="hidden"
        />
        {uploading ? (
          <Loader2 className="mx-auto w-10 h-10 text-blue-400 animate-spin" />
        ) : (
          <Upload className="mx-auto w-10 h-10 text-gray-400" />
        )}
        <p className="mt-3 text-sm font-medium text-gray-600 dark:text-gray-300">
          {uploading ? t("uploading") : t("dropHint")}
        </p>
        <p className="mt-1 text-xs text-gray-400">
          Google Scholar export, or any CSV with Title/DOI columns
        </p>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 px-3 py-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg text-sm">
          <XCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Progress Panel */}
      {batchStatus && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">
              {t("batchDownload")}
            </h3>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium
              ${batchStatus.status === "completed"
                ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
              }`}>
              {batchStatus.status === "completed" ? t("done") : t("running")}
            </span>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all duration-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>

          {/* Stats */}
          <div className="flex gap-4 text-xs text-gray-500 dark:text-gray-400">
            <span>Total: <strong>{batchStatus.total}</strong></span>
            <span className="text-green-600">✅ {batchStatus.success}</span>
            <span className="text-red-500">❌ {batchStatus.failed}</span>
            <span>{batchStatus.completed}/{batchStatus.total} processed</span>
          </div>

          {/* Results List */}
          {batchStatus.results.length > 0 && (
            <div className="max-h-60 overflow-y-auto space-y-1 mt-2">
              {batchStatus.results.map((r, i) => (
                <div key={i} className="flex items-center gap-2 text-xs py-1 px-2 rounded hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  {r.status === "success" ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-green-500 shrink-0" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-red-400 shrink-0" />
                  )}
                  <span className="font-mono text-gray-600 dark:text-gray-300 truncate">
                    {r.doi}
                  </span>
                  {r.file_size > 0 && (
                    <span className="text-gray-400 ml-auto shrink-0">
                      {(r.file_size / 1024).toFixed(0)}KB
                    </span>
                  )}
                  {r.error && (
                    <span className="text-red-400 ml-auto truncate max-w-[200px]" title={r.error}>
                      {r.error}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
