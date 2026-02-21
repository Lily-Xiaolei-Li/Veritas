/**
 * SessionList Component (B1.5)
 */

"use client";

import React from "react";
import { MessageSquare, AlertCircle, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { SessionItem } from "./SessionItem";
import type { Session } from "@/lib/api/types";

interface SessionListProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onDeleteSession: (id: string) => void;
  onRenameSession: (id: string, newTitle: string) => void;
  isLoading: boolean;
  error: Error | null;
  onRetry: () => void;
}

export function SessionList({ sessions, activeSessionId, onSelectSession, onDeleteSession, onRenameSession, isLoading, error, onRetry }: SessionListProps) {
  const t = useTranslations("sessions");

  if (isLoading && sessions.length === 0) {
    return <div className="flex-1 flex flex-col items-center justify-center p-4"><RefreshCw className="h-6 w-6 text-gray-400 animate-spin mb-2" /><p className="text-sm text-gray-500">{t("loading")}</p></div>;
  }

  if (error) {
    return <div className="flex-1 flex flex-col items-center justify-center p-4"><AlertCircle className="h-6 w-6 text-red-400 mb-2" /><p className="text-sm text-gray-700 mb-2">{t("loadFailed")}</p><button onClick={onRetry} className="text-sm text-blue-600 hover:text-blue-800 hover:underline">{t("retry")}</button></div>;
  }

  if (sessions.length === 0) {
    return <div className="flex-1 flex flex-col items-center justify-center p-4"><MessageSquare className="h-8 w-8 text-gray-300 mb-2" /><p className="text-sm text-gray-500 text-center">{t("empty")}</p></div>;
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {sessions.map((session) => (
        <SessionItem
          key={session.id}
          session={session}
          isActive={session.id === activeSessionId}
          onSelect={() => onSelectSession(session.id)}
          onDelete={() => onDeleteSession(session.id)}
          onRename={(newTitle) => onRenameSession(session.id, newTitle)}
        />
      ))}
    </div>
  );
}
