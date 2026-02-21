/**
 * DeleteConfirmationDialog Component (B1.5)
 */

"use client";

import React, { useEffect, useCallback } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/Button";

interface DeleteConfirmationDialogProps {
  isOpen: boolean;
  sessionTitle: string;
  onConfirm: () => void;
  onCancel: () => void;
  isDeleting: boolean;
}

export function DeleteConfirmationDialog({ isOpen, sessionTitle, onConfirm, onCancel, isDeleting }: DeleteConfirmationDialogProps) {
  const t = useTranslations("sessions");

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape" && !isDeleting) onCancel();
  }, [onCancel, isDeleting]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener("keydown", handleKeyDown);
      return () => document.removeEventListener("keydown", handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={isDeleting ? undefined : onCancel} />
      <div className="relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 bg-red-100 rounded-full flex items-center justify-center"><AlertTriangle className="h-5 w-5 text-red-600" /></div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">{t("deleteTitle")}</h3>
            <p className="mt-2 text-sm text-gray-600">{t("deleteAsk")} <span className="font-medium text-gray-900">&ldquo;{sessionTitle}&rdquo;</span>？</p>
            <p className="mt-1 text-sm text-gray-500">{t("deleteWarning")}</p>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" onClick={onCancel} disabled={isDeleting}>{t("cancel")}</Button>
          <Button variant="danger" onClick={onConfirm} disabled={isDeleting}>{isDeleting ? <><Loader2 className="h-4 w-4 animate-spin mr-2" />{t("deleting")}</> : t("delete")}</Button>
        </div>
      </div>
    </div>
  );
}
