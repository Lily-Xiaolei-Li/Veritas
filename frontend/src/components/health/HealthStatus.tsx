"use client";

import React from "react";
import { CheckCircle, XCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { useHealth } from "@/lib/hooks/useHealth";

export function HealthStatus() {
  const t = useTranslations("health");
  const { data, isLoading, isError, error } = useHealth();

  if (isLoading) return <Card><CardHeader><CardTitle>{t("systemHealth")}</CardTitle></CardHeader><CardContent><p className="text-gray-600">{t("checkingBackend")}</p></CardContent></Card>;

  if (isError || !data) {
    return (
      <Card variant="bordered">
        <CardHeader><CardTitle className="text-red-600">{t("backendOffline")}</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-start gap-3">
            <XCircle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-gray-700 font-medium">{t("cannotConnect")}</p>
              <p className="text-sm text-gray-600 mt-1">{error?.message || t("ensureBackend")}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const getStatusVariant = (status: string) => status === "healthy" ? "success" : status === "degraded" ? "warning" : "error";

  return (
    <Card variant="bordered">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>{t("systemHealth")}</CardTitle>
          <Badge variant={getStatusVariant(data.status)} size="sm">{data.status.toUpperCase()}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {data.raw?.docker !== undefined && <CheckItem name={t("docker")} ok={data.raw.docker.ok} detail={data.raw.docker.ok ? t("dockerRunning") : t("dockerUnavailable")} />}
        {data.raw?.database !== undefined && <CheckItem name={t("database")} ok={data.raw.database.ok} detail={data.raw.database.ok ? t("databaseConnected") : t("databaseUnavailable")} />}
        {data.raw?.resources !== undefined && <CheckItem name={t("resources")} ok={data.raw.resources.ok} detail={data.raw.resources.ok ? t("resourcesOk") : t("resourceConstraints")} />}
      </CardContent>
    </Card>
  );
}

interface CheckItemProps { name: string; ok: boolean; detail: string; }

function CheckItem({ name, ok, detail }: CheckItemProps) {
  return (
    <div className="flex items-start gap-3 p-2 rounded-lg hover:bg-gray-50">
      {ok ? <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" /> : <XCircle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">{name}</p>
        <p className="text-sm text-gray-600">{detail}</p>
      </div>
    </div>
  );
}
