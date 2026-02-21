import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { authFetch } from "@/lib/api/authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";

export type ProviderConfig = {
  provider: string;
  config: Record<string, unknown>;
};

export function useLLMProviderConfig(provider: string) {
  return useQuery({
    queryKey: ["llm-provider-config", provider],
    queryFn: async (): Promise<ProviderConfig> => {
      const res = await authFetch(`${API_BASE_URL}/api/v1/llm/providers/${provider}/config`);
      if (!res.ok) throw new Error(await res.text().catch(() => "Failed to load provider config"));
      return res.json();
    },
    enabled: !!provider,
    staleTime: 10_000,
  });
}

export function useUpsertLLMProviderConfig(provider: string) {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { config: Record<string, unknown>; apiKey?: string | null }) => {
      const res = await authFetch(`${API_BASE_URL}/api/v1/llm/providers/${provider}/config`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(await res.text().catch(() => "Failed to save provider config"));
      return res.json() as Promise<ProviderConfig>;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llm-provider-config", provider] });
    },
  });
}
