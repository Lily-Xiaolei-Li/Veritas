/**
 * Health Status Component
 *
 * Detailed display of backend health check results.
 * B1.1 update - Simplified to work with actual useHealth data structure.
 */

"use client";

import React from "react";
import { CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { useHealth } from "@/lib/hooks/useHealth";

export function HealthStatus() {
  const { data, isLoading, isError, error } = useHealth();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>System Health</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">Checking backend status...</p>
        </CardContent>
      </Card>
    );
  }

  if (isError || !data) {
    return (
      <Card variant="bordered">
        <CardHeader>
          <CardTitle className="text-red-600">Backend Offline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-start gap-3">
            <XCircle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-gray-700 font-medium">Cannot connect to backend</p>
              <p className="text-sm text-gray-600 mt-1">
                {error?.message || "Make sure the backend is running on port 8000"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  const getStatusVariant = (status: string) => {
    switch (status) {
      case "healthy":
        return "success";
      case "degraded":
        return "warning";
      default:
        return "error";
    }
  };

  return (
    <Card variant="bordered">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>System Health</CardTitle>
          <Badge variant={getStatusVariant(data.status)} size="sm">
            {data.status.toUpperCase()}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Docker Status */}
        {data.raw?.docker !== undefined && (
          <CheckItem
            name="Docker"
            ok={data.raw.docker.ok}
            detail={data.raw.docker.ok ? "Docker is running" : "Docker is not available"}
          />
        )}

        {/* Database Status */}
        {data.raw?.database !== undefined && (
          <CheckItem
            name="Database"
            ok={data.raw.database.ok}
            detail={data.raw.database.ok ? "Database connected" : "Database unavailable"}
          />
        )}

        {/* Resources Status */}
        {data.raw?.resources !== undefined && (
          <CheckItem
            name="Resources"
            ok={data.raw.resources.ok}
            detail={data.raw.resources.ok ? "System resources OK" : "Resource constraints"}
          />
        )}
      </CardContent>
    </Card>
  );
}

interface CheckItemProps {
  name: string;
  ok: boolean;
  detail: string;
}

function CheckItem({ name, ok, detail }: CheckItemProps) {
  return (
    <div className="flex items-start gap-3 p-2 rounded-lg hover:bg-gray-50">
      {ok ? (
        <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
      ) : (
        <XCircle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">{name}</p>
        <p className="text-sm text-gray-600">{detail}</p>
      </div>
    </div>
  );
}
