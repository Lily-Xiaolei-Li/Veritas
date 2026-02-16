import { authFetch } from "./authFetch";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export type VFAgent = {
  name: string;
  description: string;
  model: string;
};

export type VFGenerateRequest = {
  paper_id: string;
  metadata?: Record<string, unknown>;
  abstract?: string;
  full_text?: string;
  in_library?: boolean;
  agent?: string;
};

export async function fetchVFStats() {
  const res = await authFetch(`${API_BASE}/api/v1/vf/stats`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchVFList(limit = 50, offset = 0) {
  const res = await authFetch(`${API_BASE}/api/v1/vf/list?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchVFAgents(): Promise<{ agents: VFAgent[] }> {
  const res = await authFetch(`${API_BASE}/api/v1/vf/agents`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function lookupVFProfile(paperId: string) {
  const res = await authFetch(`${API_BASE}/api/v1/vf/lookup?paper_id=${encodeURIComponent(paperId)}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function generateVFProfile(req: VFGenerateRequest) {
  const res = await authFetch(`${API_BASE}/api/v1/vf/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function deleteVFProfile(paperId: string) {
  const res = await authFetch(`${API_BASE}/api/v1/vf/${encodeURIComponent(paperId)}`, { method: "DELETE" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function syncVFProfiles(
  body: { library_path?: string; agent?: string; dry_run?: boolean },
  onMessage: (event: Record<string, unknown>) => void,
) {
  const res = await authFetch(`${API_BASE}/api/v1/vf/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) throw new Error(await res.text());
  if (!res.body) return;

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const dataLine = part
        .split("\n")
        .map((line) => line.trim())
        .find((line) => line.startsWith("data:"));

      if (!dataLine) continue;
      const payload = dataLine.slice(5).trim();
      if (!payload) continue;

      try {
        onMessage(JSON.parse(payload));
      } catch {
        // ignore malformed chunks
      }
    }
  }
}
