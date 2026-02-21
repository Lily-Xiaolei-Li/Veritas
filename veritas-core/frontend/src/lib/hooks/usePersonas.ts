/**
 * Personas hooks (Phase 6)
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/lib/utils/constants";
import { authFetch } from "@/lib/api/authFetch";
import type { Persona } from "@/lib/personas/registry";

export interface PersonasListResponse {
  personas: Array<Persona & { sort_order?: number }>;
}

async function fetchPersonas(): Promise<PersonasListResponse> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/personas`);
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `Failed to fetch personas (${res.status})`);
  }
  return res.json();
}

async function createPersonaApi(body: { id: string; label: string; system_prompt: string }): Promise<Persona> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/personas`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `Failed to create persona (${res.status})`);
  }
  return res.json();
}

async function updatePersonaApi(args: { id: string; label?: string; system_prompt?: string }): Promise<Persona> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/personas/${args.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label: args.label, system_prompt: args.system_prompt }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || `Failed to update persona (${res.status})`);
  }
  return res.json();
}

async function deletePersonaApi(id: string): Promise<void> {
  const res = await authFetch(`${API_BASE_URL}/api/v1/personas/${id}`, {
    method: "DELETE",
  });
  if (!res.ok && res.status !== 204) {
    const t = await res.text();
    throw new Error(t || `Failed to delete persona (${res.status})`);
  }
}

export function usePersonas() {
  return useQuery({
    queryKey: ["personas"],
    queryFn: fetchPersonas,
    staleTime: 10_000,
    refetchOnWindowFocus: false,
  });
}

export function useCreatePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createPersonaApi,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
  });
}

export function useUpdatePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: updatePersonaApi,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
  });
}

export function useDeletePersona() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deletePersonaApi,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["personas"] });
    },
  });
}
