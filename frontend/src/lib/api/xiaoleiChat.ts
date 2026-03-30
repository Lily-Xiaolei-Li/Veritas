/**
 * XiaoLei Chat API Client
 *
 * Streams responses over SSE from POST /api/chat.
 */

import { API_BASE_URL } from "@/lib/utils/constants";

export interface EditTargetSelection {
  artifactId: string;
  startLine: number;
  endLine: number;
  text: string;
}

export interface XiaoLeiChatRequest {
  message: string;
  context?: string;
  button_prompt?: string;
  system_prompt?: string;  // Persona system prompt for AI behavior
  model?: string;          // HASHI API model override
  // Edit target (B1.7 - Edit Toggle)
  edit_target_artifact_id?: string;
  edit_target_artifact_name?: string;
  edit_target_artifact_content?: string;
  edit_target_selections?: EditTargetSelection[];
}

export type XiaoLeiChatEvent =
  | { type: "token"; content: string }
  | { type: "artifact"; content: string; filename?: string }
  | { type: "done" }
  | { type: "error"; message?: string };

// OpenAI-compatible SSE format (used by Gateway)
interface OpenAIStreamChunk {
  id?: string;
  object?: string;
  choices?: Array<{
    delta?: { content?: string; role?: string };
    finish_reason?: string | null;
  }>;
}

/**
 * Parse SSE data - supports both custom format and OpenAI format
 */
function parseSSEData(dataText: string): XiaoLeiChatEvent | null {
  // Handle [DONE] marker from OpenAI format
  if (dataText.trim() === "[DONE]") {
    return { type: "done" };
  }

  try {
    const parsed = JSON.parse(dataText);

    // Check if it's our custom format (has 'type' field)
    if ("type" in parsed) {
      return parsed as XiaoLeiChatEvent;
    }

    // Check if it's OpenAI format (has 'choices' array)
    if ("choices" in parsed && Array.isArray(parsed.choices)) {
      const chunk = parsed as OpenAIStreamChunk;
      const choice = chunk.choices?.[0];

      if (choice?.finish_reason === "stop") {
        return { type: "done" };
      }

      const content = choice?.delta?.content;
      if (content !== undefined && content !== null) {
        return { type: "token", content };
      }

      // Role-only delta (first chunk), skip it
      return null;
    }

    // Unknown format, try to extract content
    if ("content" in parsed && typeof parsed.content === "string") {
      return { type: "token", content: parsed.content };
    }

    return null;
  } catch {
    return null;
  }
}

export interface XiaoLeiChatHandlers {
  onOpen?: () => void;
  onToken: (content: string) => void;
  onArtifact?: (content: string, filename?: string) => void;
  onDone?: () => void;
  onError?: (message: string) => void;
  signal?: AbortSignal;
}

export async function streamXiaoLeiChat(
  payload: XiaoLeiChatRequest,
  handlers: XiaoLeiChatHandlers
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal: handlers.signal,
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "");
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }

  if (!response.body) {
    throw new Error("No response body for SSE stream");
  }

  handlers.onOpen?.();

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let doneReceived = false;

  const processChunk = (chunk: string) => {
    const lines = chunk.split(/\r?\n/);

    for (const line of lines) {
      if (!line.startsWith("data:")) continue;

      const dataText = line.slice(5).trimStart();
      if (!dataText) continue;

      const event = parseSSEData(dataText);
      if (!event) continue;

      switch (event.type) {
        case "token":
          handlers.onToken(event.content || "");
          break;
        case "artifact":
          handlers.onArtifact?.(event.content || "", event.filename);
          break;
        case "done":
          doneReceived = true;
          handlers.onDone?.();
          break;
        case "error":
          handlers.onError?.(event.message || "Unknown error");
          break;
        default:
          break;
      }
    }
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split(/\r?\n\r?\n/);
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      processChunk(part);
      if (doneReceived) break;
    }

    if (doneReceived) break;
  }

  if (!doneReceived && buffer.trim().length > 0) {
    processChunk(buffer);
  }

  if (doneReceived) {
    await reader.cancel().catch(() => undefined);
  }
}
