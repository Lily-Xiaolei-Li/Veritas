/**
 * SessionItem Component (B1.5)
 */

"use client";

import React, { useState, useRef, useEffect } from "react";
import { MessageSquare, Pencil, Trash2, Check, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils/cn";
import type { Session } from "@/lib/api/types";

interface SessionItemProps {
  session: Session;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename: (newTitle: string) => void;
}

function formatRelativeDate(dateString: string, t: ReturnType<typeof useTranslations>): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return t("justNow");
  if (diffMins < 60) return t("minutesAgo", { count: diffMins });
  if (diffHours < 24) return t("hoursAgo", { count: diffHours });
  if (diffDays < 7) return t("daysAgo", { count: diffDays });

  return date.toLocaleDateString();
}

export function SessionItem({ session, isActive, onSelect, onDelete, onRename }: SessionItemProps) {
  const t = useTranslations("sessions");
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(session.title || "");
  const inputRef = useRef<HTMLInputElement>(null);

  const displayTitle = session.title || t("untitled");

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  const handleStartEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditValue(session.title || "");
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditValue(session.title || "");
  };

  const handleSaveEdit = () => {
    const trimmed = editValue.trim();
    if (trimmed && trimmed !== session.title) onRename(trimmed);
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSaveEdit();
    else if (e.key === "Escape") handleCancelEdit();
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete();
  };

  if (isEditing) {
    return (
      <div className={cn("flex items-center gap-2 px-3 py-2 border-l-2", isActive ? "border-l-blue-500 bg-blue-50" : "border-l-transparent")}>
        <input ref={inputRef} type="text" value={editValue} onChange={(e) => setEditValue(e.target.value)} onKeyDown={handleKeyDown} onBlur={handleSaveEdit} className="flex-1 min-w-0 px-2 py-1 text-sm border border-blue-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500" />
        <button onClick={handleSaveEdit} className="p-1 text-green-600 hover:bg-green-100 rounded" title={t("save")}><Check className="h-4 w-4" /></button>
        <button onClick={handleCancelEdit} className="p-1 text-gray-500 hover:bg-gray-100 rounded" title={t("cancel")}><X className="h-4 w-4" /></button>
      </div>
    );
  }

  return (
    <div className={cn("group flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors border-l-2", "hover:bg-gray-100", isActive ? "border-l-blue-500 bg-blue-50 hover:bg-blue-100" : "border-l-transparent")} onClick={onSelect}>
      <MessageSquare className={cn("h-4 w-4 flex-shrink-0", isActive ? "text-blue-600" : "text-gray-400")} />
      <div className="flex-1 min-w-0">
        <div className={cn("text-sm font-medium truncate", isActive ? "text-blue-900" : "text-gray-900")} title={displayTitle}>{displayTitle}</div>
        <div className="text-xs text-gray-500">{formatRelativeDate(session.updated_at, t)}</div>
      </div>
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button onClick={handleStartEdit} className="p-1 text-gray-400 hover:text-blue-600 hover:bg-blue-100 rounded" title={t("rename")}><Pencil className="h-3.5 w-3.5" /></button>
        <button onClick={handleDelete} className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-100 rounded" title={t("delete")}><Trash2 className="h-3.5 w-3.5" /></button>
      </div>
    </div>
  );
}
