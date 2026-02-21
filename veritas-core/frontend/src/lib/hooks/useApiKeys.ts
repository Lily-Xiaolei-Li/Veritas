/**
 * API Keys Hooks (B1.6 - Authentication & API Key UI)
 *
 * React Query hooks for API key management:
 * - useApiKeys: Query for listing API keys
 * - useCreateApiKey: Mutation for creating a new API key
 * - useDeleteApiKey: Mutation for deleting an API key
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/lib/utils/constants";
import { authFetch } from "@/lib/api/authFetch";
import type { ApiKey, ApiKeyCreate, ApiKeyListParams } from "@/lib/api/types";

// =============================================================================
// API Functions
// =============================================================================

/**
 * Fetch API keys from backend.
 */
async function fetchApiKeys(params: ApiKeyListParams = {}): Promise<ApiKey[]> {
  const searchParams = new URLSearchParams();

  if (params.provider) {
    searchParams.set("provider", params.provider);
  }
  if (params.active_only !== undefined) {
    searchParams.set("active_only", String(params.active_only));
  }

  const queryString = searchParams.toString();
  const url = `${API_BASE_URL}/api/v1/auth/api-keys${queryString ? `?${queryString}` : ""}`;

  const response = await authFetch(url);

  if (!response.ok) {
    const error = await response.text().catch(() => "Unknown error");
    throw new Error(`Failed to fetch API keys: ${error}`);
  }

  return response.json();
}

/**
 * Create a new API key.
 */
async function createApiKey(data: ApiKeyCreate): Promise<ApiKey> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/auth/api-keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create API key: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Delete an API key.
 */
async function deleteApiKey(keyId: string): Promise<void> {
  const response = await authFetch(`${API_BASE_URL}/api/v1/auth/api-keys/${keyId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete API key: ${response.statusText}`);
  }
}

// =============================================================================
// React Query Hooks
// =============================================================================

/**
 * Hook for fetching API keys.
 *
 * @param params - Optional filter parameters
 * @param options - React Query options
 */
export function useApiKeys(params: ApiKeyListParams = {}) {
  return useQuery({
    queryKey: ["api-keys", params],
    queryFn: () => fetchApiKeys(params),
    staleTime: 60000, // 1 minute
  });
}

/**
 * Hook for creating a new API key.
 */
export function useCreateApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createApiKey,
    onSuccess: () => {
      // Invalidate API keys cache to refetch
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
}

/**
 * Hook for deleting an API key.
 */
export function useDeleteApiKey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteApiKey,
    onSuccess: () => {
      // Invalidate API keys cache to refetch
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });
}
