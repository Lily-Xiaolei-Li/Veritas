"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRuns, useResumeRun, canResumeRun, getStatusLabel, getStatusColor } from "@/lib/hooks/useRuns";
import type { Run } from "@/lib/api/types";
import { Play, RefreshCw, Clock, CheckCircle, XCircle, AlertTriangle, Pause } from "lucide-react";

interface RunHistoryProps { sessionId: string | null; }

export function RunHistory({ sessionId }: RunHistoryProps) {
  const t = useTranslations("runs");
  const [page, setPage] = useState(0);
  const pageSize = 10;
  const { data, isLoading, error, refetch } = useRuns(sessionId, { limit: pageSize, offset: page * pageSize });
  const resumeMutation = useResumeRun();

  const handleResume = async (run: Run) => {
    try { await resumeMutation.mutateAsync(run.id); } catch (err) { console.error("Failed to resume run:", err); }
  };

  if (!sessionId) return <div className="p-4 text-gray-500 text-sm">{t("selectSession")}</div>;
  if (isLoading) return <div className="p-4 text-gray-500 text-sm">{t("loading")}</div>;
  if (error) return <div className="p-4 text-red-500 text-sm">{t("loadError")}: {(error as Error).message}</div>;

  const runs = data?.runs || [];
  const total = data?.total || 0;
  const totalPages = Math.ceil(total / pageSize);

  if (runs.length === 0) return <div className="p-4 text-gray-500 text-sm">{t("empty")}</div>;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-2 border-b border-gray-700">
        <span className="text-sm font-medium text-gray-300">{t("title", { total })}</span>
        <button onClick={() => refetch()} className="p-1 text-gray-400 hover:text-gray-200 rounded" title={t("refresh")}><RefreshCw className="h-4 w-4" /></button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {runs.map((run) => <RunItem key={run.id} run={run} onResume={() => handleResume(run)} isResuming={resumeMutation.isPending && resumeMutation.variables === run.id} />)}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between p-2 border-t border-gray-700">
          <button onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0} className="px-2 py-1 text-xs bg-gray-700 rounded disabled:opacity-50">{t("previous")}</button>
          <span className="text-xs text-gray-400">{t("page", { current: page + 1, total: totalPages })}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} className="px-2 py-1 text-xs bg-gray-700 rounded disabled:opacity-50">{t("next")}</button>
        </div>
      )}
    </div>
  );
}

interface RunItemProps { run: Run; onResume: () => void; isResuming: boolean; }

function RunItem({ run, onResume, isResuming }: RunItemProps) {
  const t = useTranslations("runs");
  const showResume = canResumeRun(run);

  return (
    <div className="p-3 border-b border-gray-800 hover:bg-gray-800/50">
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <StatusIcon status={run.status} />
          <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(run.status)} text-white`}>{getStatusLabel(run.status)}</span>
          {run.has_checkpoints && <span className="text-xs text-gray-500" title={t("hasCheckpoints")}><Pause className="h-3 w-3 inline" /></span>}
        </div>
        {showResume && <button onClick={onResume} disabled={isResuming} className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 hover:bg-blue-500 rounded disabled:opacity-50"><Play className="h-3 w-3" />{isResuming ? t("resuming") : t("resume")}</button>}
      </div>

      <p className="text-sm text-gray-300 truncate mb-1">{run.task}</p>

      <div className="flex items-center gap-3 text-xs text-gray-500">
        <span title={t("created")}>{formatTime(run.created_at)}</span>
        {run.started_at && <span title={t("started")}>{t("startedAt")}: {formatTime(run.started_at)}</span>}
        {run.completed_at && <span title={t("completed")}>{t("endedAt")}: {formatTime(run.completed_at)}</span>}
      </div>

      {run.error && <p className="mt-1 text-xs text-red-400 truncate" title={run.error}>{t("error")}: {run.error}</p>}
    </div>
  );
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case "pending": return <Clock className="h-4 w-4 text-gray-400" />;
    case "running": return <RefreshCw className="h-4 w-4 text-blue-400 animate-spin" />;
    case "completed": return <CheckCircle className="h-4 w-4 text-green-400" />;
    case "failed": return <XCircle className="h-4 w-4 text-red-400" />;
    case "terminated": return <AlertTriangle className="h-4 w-4 text-yellow-400" />;
    case "interrupted": return <AlertTriangle className="h-4 w-4 text-orange-400" />;
    default: return <Clock className="h-4 w-4 text-gray-400" />;
  }
}

function formatTime(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
