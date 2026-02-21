/**
 * Health Check Hook
 *
 * B1.0 - Workbench Shell
 */

import { useQuery } from "@tanstack/react-query";
import { API_BASE_URL, HEALTH_CHECK_INTERVAL } from "@/lib/utils/constants";

interface HealthResponse {
  status: string;
  docker?: {
    ok: boolean;
  };
  resources?: {
    ok: boolean;
  };
  database?: {
    ok: boolean;
  };
}

interface HealthData {
  status: "healthy" | "degraded" | "unhealthy";
  raw: HealthResponse;
}

async function fetchHealth(): Promise<HealthData> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }

  const data: HealthResponse = await response.json();

  // Map backend status to frontend status
  // Backend returns "ok", frontend expects "healthy"
  let status: "healthy" | "degraded" | "unhealthy" = "unhealthy";

  if (data.status === "ok" || data.status === "healthy") {
    status = "healthy";
  } else if (data.status === "degraded") {
    status = "degraded";
  }

  return {
    status,
    raw: data,
  };
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: HEALTH_CHECK_INTERVAL,
    retry: 1,
    staleTime: 10000,
  });
}
