import { useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/lib/utils/constants";
import { authFetch } from "@/lib/api/authFetch";

async function reorderPersonasApi(orderedIds: string[]): Promise<void> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/personas/reorder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ordered_ids: orderedIds }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `Failed to reorder personas (${res.status})`);
  }
}

export function useReorderPersonas() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: reorderPersonasApi,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
  });
}
