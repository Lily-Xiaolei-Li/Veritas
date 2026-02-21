/**
 * Kill Switch Button (B1.4)
 *
 * Always-visible button in the header that terminates the active run.
 * Uses two-step confirmation: first click primes, second click confirms.
 * Timeout resets after 3 seconds if not confirmed.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { Square, Loader2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useKillSwitch } from "@/lib/hooks/useKillSwitch";
import { cn } from "@/lib/utils/cn";

interface KillSwitchButtonProps {
  className?: string;
}

export function KillSwitchButton({ className }: KillSwitchButtonProps) {
  const t = useTranslations("killSwitch");
  const { terminate, isTerminating, canTerminate } = useKillSwitch();
  const [isPrimed, setIsPrimed] = useState(false);
  const [confirmTimeout, setConfirmTimeout] = useState<NodeJS.Timeout | null>(
    null
  );

  // Reset primed state after 3 seconds
  useEffect(() => {
    if (isPrimed) {
      const timeout = setTimeout(() => {
        setIsPrimed(false);
      }, 3000);
      setConfirmTimeout(timeout);

      return () => clearTimeout(timeout);
    }
  }, [isPrimed]);

  // Clear timeout on unmount
  useEffect(() => {
    return () => {
      if (confirmTimeout) {
        clearTimeout(confirmTimeout);
      }
    };
  }, [confirmTimeout]);

  const handleClick = useCallback(() => {
    if (isTerminating) return;

    if (isPrimed) {
      // Second click - confirm termination
      terminate();
      setIsPrimed(false);
      if (confirmTimeout) {
        clearTimeout(confirmTimeout);
        setConfirmTimeout(null);
      }
    } else {
      // First click - prime the button
      setIsPrimed(true);
    }
  }, [isPrimed, isTerminating, terminate, confirmTimeout]);

  // Don't render if no active execution
  if (!canTerminate && !isTerminating) {
    return null;
  }

  return (
    <button
      onClick={handleClick}
      disabled={isTerminating}
      className={cn(
        "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-sm font-medium transition-all",
        // Base state
        !isPrimed &&
          !isTerminating &&
          "bg-red-100 text-red-700 hover:bg-red-200 border border-red-300",
        // Primed state (waiting for confirmation)
        isPrimed &&
          !isTerminating &&
          "bg-red-600 text-white hover:bg-red-700 border border-red-700 animate-pulse",
        // Terminating state
        isTerminating &&
          "bg-gray-200 text-gray-500 cursor-not-allowed border border-gray-300",
        className
      )}
      title={
        isTerminating
          ? t("stopping")
          : isPrimed
            ? t("confirmHint")
            : t("stopHint")
      }
    >
      {isTerminating ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>{t("stopping")}</span>
        </>
      ) : isPrimed ? (
        <>
          <Square className="h-4 w-4 fill-current" />
          <span>{t("confirmStop")}</span>
        </>
      ) : (
        <>
          <Square className="h-4 w-4" />
          <span>{t("stop")}</span>
        </>
      )}
    </button>
  );
}
