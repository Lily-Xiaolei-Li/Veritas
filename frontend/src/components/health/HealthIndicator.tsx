"use client";

import React from "react";
import { Circle } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils/cn";
import { useHealth } from "@/lib/hooks/useHealth";

interface HealthIndicatorProps { className?: string; showLabel?: boolean; }

export function HealthIndicator({ className, showLabel = false }: HealthIndicatorProps) {
  const t = useTranslations("health");
  const { data, isLoading, isError } = useHealth();

  const getStatus = () => {
    if (isLoading) return { color: "text-gray-400", label: t("checking") };
    if (isError) return { color: "text-red-500", label: t("offline") };
    if (data?.status === "healthy") return { color: "text-green-500", label: t("healthy") };
    if (data?.status === "degraded") return { color: "text-yellow-500", label: t("degraded") };
    return { color: "text-red-500", label: t("unhealthy") };
  };

  const status = getStatus();

  return <div className={cn("flex items-center gap-2", className)}><Circle className={cn("h-3 w-3 fill-current", status.color)} aria-label={status.label} />{showLabel && <span className="text-sm font-medium text-gray-700 dark:text-gray-200">{status.label}</span>}</div>;
}
