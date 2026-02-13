/**
 * LLM utility API (Stage 12)
 */

import { authFetch } from "./authFetch";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface LLMTestRequest {
  provider: string;
  model?: string | null;
}

export interface LLMTestResponse {
  ok: boolean;
  provider: string;
  model: string;
  latency_ms?: number | null;
  error?: string | null;
}

export async function testLLMProvider(req: LLMTestRequest): Promise<LLMTestResponse> {
  const res = await authFetch(`${API_BASE}/api/v1/llm/test`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const t = await res.text();
    throw new Error(t || "Failed to test provider");
  }

  return res.json();
}
