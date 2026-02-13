/**
 * Reasoning Panel Component (B1.1 - Streaming Reasoning & Events)
 *
 * Left panel - displays chat messages and streaming agent responses.
 *
 * Features:
 * - Message history display
 * - Real-time streaming message with cursor indicator
 * - Auto-scroll with manual override
 * - Message input form
 */

"use client";

import React, { useRef, useEffect, useState, FormEvent, KeyboardEvent } from "react";
import { MessageSquare, Send, ChevronRight, Square, FileText } from "lucide-react";
import { Button } from "../ui/Button";
import { PersonaSelector, getPersonaById } from "@/components/chat/PersonaSelector";
import { useWorkbenchStore } from "@/lib/store";
import { useSessionArtifacts, useSaveArtifact } from "@/lib/hooks/useArtifacts";
import { useQueryClient } from "@tanstack/react-query";
import { useLLMProviderConfig } from "@/lib/hooks/useLLMProviderConfig";
import { streamXiaoLeiChat } from "@/lib/api/xiaoleiChat";
import { authFetch } from "@/lib/api/authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";
import type { ArtifactPreviewKind } from "@/lib/api/types";
import type { LocalArtifact } from "@/lib/artifacts/types";

interface ReasoningPanelProps {
  onCollapse?: () => void;
}

export function ReasoningPanel({ onCollapse }: ReasoningPanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [inputValue, setInputValue] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const [showJumpButton, setShowJumpButton] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);
  const [chatMode, setChatMode] = useState<"xiaolei" | "openrouter">("xiaolei");
  const [openrouterModel, setOpenrouterModel] = useState<string>("");

  const saveArtifactMutation = useSaveArtifact();
  const queryClient = useQueryClient();

  // Phase 4: Artifact emission protocol (LLM writes files directly)
  const ARTIFACT_PROTOCOL =
    "If the user asks you to create/save a file, output it using this exact format (and nothing else inside the block):\n" +
    "<<<ARTIFACT:filename.ext>>>\n" +
    "<file content>\n" +
    "<<<END_ARTIFACT>>>\n\n" +
    "Rules: filename must include an extension; do not wrap in markdown code fences; you may output multiple artifact blocks.";


  // Store state
  const {
    currentSessionId,
    messages,
    streamingMessage,
    sseError,
    addMessage,
    appendToStreamingMessage,
    finalizeStreamingMessage,
    setSSEConnected,
    setSSEError,
    addLocalArtifact,
    localArtifacts,
    focusedArtifactIds,
    textSelections,
    clearTextSelections,
    clearFocusedArtifacts,
    selectedPersonaId,
    setSelectedPersona,
    setOutboundPreview,
    // Edit target (B1.7)
    editTargetArtifactId,
    editTargetSelections,
    setEditTarget,
    clearEditTargetSelections,
  } = useWorkbenchStore();

  // Provider config (Phase 2)
  const { data: openrouterCfg } = useLLMProviderConfig("openrouter");

  const openrouterModels: Array<{ id: string; name?: string }> = React.useMemo(() => {
    const models = openrouterCfg?.config?.models;
    if (!Array.isArray(models)) return [];
    return models
      .map((m: unknown) => {
        const obj = (m && typeof m === "object") ? (m as Record<string, unknown>) : {};
        const id = typeof obj.id === "string" ? obj.id : String(obj.id || "");
        const name = typeof obj.name === "string" ? obj.name : undefined;
        return { id, name };
      })
      .filter((m) => m.id);
  }, [openrouterCfg?.config?.models]);

  // Default model selection
  useEffect(() => {
    if (openrouterModel) return;
    if (openrouterModels.length > 0) {
      setOpenrouterModel(openrouterModels[0].id);
    }
  }, [openrouterModel, openrouterModels]);

  // Get artifacts to calculate focused artifact sizes
  const { data: artifactsData } = useSessionArtifacts(currentSessionId, { limit: 500 });

  // Calculate total context size (artifacts + selections)
  const contextStats = React.useMemo(() => {
    let totalChars = 0;
    const itemCount = focusedArtifactIds.length + textSelections.length;
    
    // Count focused artifacts size (size_bytes ≈ chars for text files)
    if (artifactsData?.artifacts) {
      focusedArtifactIds.forEach((id) => {
        const artifact = artifactsData.artifacts.find((a) => a.id === id);
        if (artifact) {
          totalChars += artifact.size_bytes;
        }
      });
    }
    
    // Count text selections
    textSelections.forEach((sel) => {
      totalChars += sel.text.length;
    });

    // Format size
    const formatSize = (chars: number) => {
      if (chars < 1000) return `${chars} chars`;
      if (chars < 10000) return `${(chars / 1000).toFixed(1)}k chars`;
      return `${Math.round(chars / 1000)}k chars`;
    };

    return {
      itemCount,
      totalChars,
      formattedSize: formatSize(totalChars),
      hasContent: itemCount > 0,
    };
  }, [focusedArtifactIds, textSelections, artifactsData?.artifacts]);

  // Phase 2: Keep Events panel Outbound Preview live while user edits inputs / context.
  // This is intentionally lightweight (no extra network calls): we use metadata for focused artifacts,
  // and full text for selections (since it's already in memory).
  useEffect(() => {
    const contextChunks: { label: string; preview: string }[] = [];

    // Focused artifacts (metadata-only; try local content first if available)
    if (focusedArtifactIds.length > 0) {
      for (const id of focusedArtifactIds) {
        const local = localArtifacts.find((a) => a.id === id);
        if (local?.content) {
          const label = `Artifact: ${local.display_name}`;
          contextChunks.push({ label, preview: local.content.slice(0, 800) });
          continue;
        }

        const meta = artifactsData?.artifacts?.find((a) => a.id === id);
        const displayName = meta?.display_name || id;
        const size = meta?.size_bytes != null ? `${meta.size_bytes} bytes` : "";
        const label = `Artifact: ${displayName}`;
        contextChunks.push({ label, preview: size ? `(${size})` : "(focused)" });
      }
    }

    // Text selections (in-memory previews)
    if (textSelections.length > 0) {
      for (const sel of textSelections) {
        const label = `Selection: ${sel.artifactName} (lines ${sel.startLine}-${sel.endLine})`;
        contextChunks.push({ label, preview: sel.text.slice(0, 800) });
      }
    }

    setOutboundPreview({
      persona_id: selectedPersonaId,
      user_message: inputValue,
      context_chunks: contextChunks,
    });
  }, [
    selectedPersonaId,
    inputValue,
    focusedArtifactIds,
    textSelections,
    artifactsData?.artifacts,
    localArtifacts,
    setOutboundPreview,
  ]);

  // Auto-scroll when new content arrives
  useEffect(() => {
    if (!containerRef.current || !autoScroll) return;
    containerRef.current.scrollTop = containerRef.current.scrollHeight;
  }, [messages, streamingMessage?.content, autoScroll]);

  useEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
        abortRef.current = null;
      }
    };
  }, []);

  // Detect manual scroll
  const handleScroll = () => {
    if (!containerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

    // If user scrolled up more than 50px, disable auto-scroll
    if (distanceFromBottom > 50) {
      setAutoScroll(false);
      setShowJumpButton(true);
    } else {
      setAutoScroll(true);
      setShowJumpButton(false);
    }
  };

  const jumpToLatest = () => {
    if (!containerRef.current) return;
    containerRef.current.scrollTop = containerRef.current.scrollHeight;
    setAutoScroll(true);
    setShowJumpButton(false);
  };

  // Save chat content as artifact
  const handleSaveAsArtifact = (content: string, filename: string, extension: string) => {
    const createdAt = new Date().toISOString();
    const fullFilename = `${filename}.${extension}`;
    const contentBytes = new TextEncoder().encode(content).length;
    const artifactId = `chat-saved-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    
    const previewKind: ArtifactPreviewKind = (() => {
      if (extension === "md" || extension === "markdown") return "markdown";
      if (extension === "json") return "code";
      return "text";
    })();

    const localArtifact: LocalArtifact = {
      id: artifactId,
      run_id: `saved-${Date.now()}`,
      session_id: currentSessionId || "local",
      display_name: fullFilename,
      storage_path: `chat/${artifactId}`,
      extension: extension,
      size_bytes: contentBytes,
      content_hash: null,
      mime_type: extension === "json" ? "application/json" : "text/plain",
      artifact_type: "file",
      created_at: createdAt,
      artifact_meta: { source: "chat-saved" },
      is_deleted: false,
      can_preview: true,
      preview_kind: previewKind,
      download_url: "",
      source: "chat",
      content: content,
      filename: fullFilename,
    };
    
    addLocalArtifact(localArtifact);
  };

  // Helper to save message to database for conversation history
  const saveMessageToDb = async (role: "user" | "assistant" | "system", content: string) => {
    if (!currentSessionId) return;
    try {
      await authFetch(`${API_BASE_URL}/api/v1/sessions/${currentSessionId}/messages/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role, content }),
      });
    } catch (e) {
      console.error("Failed to save message to DB:", e);
      // Don't block chat if save fails
    }
  };

  const sendMessage = async (rawContent: string, options?: { clearInput?: boolean }) => {
    const content = rawContent.trim();

    if (!content || isStreaming) return;
    if (!currentSessionId) {
      setSendError("No session selected");
      return;
    }

    setSendError(null);
    setSSEError(null);

    // Add user message immediately
    addMessage({
      id: `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      session_id: currentSessionId || "",
      role: "user",
      content,
      created_at: new Date().toISOString(),
    });

    // Save user message to DB for conversation history
    void saveMessageToDb("user", content);

    if (options?.clearInput) {
      setInputValue("");
      textareaRef.current?.focus();
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }

    const runId = `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const controller = new AbortController();
    abortRef.current = controller;
    setIsStreaming(true);

    try {
      // Get persona system prompt
      const persona = getPersonaById(selectedPersonaId);
      const systemPrompt = `${persona.system_prompt}\n\n${ARTIFACT_PROTOCOL}`;

      // Build context from focused artifacts and text selections
      const contextParts: string[] = [];
      const contextChunks: { label: string; preview: string }[] = [];

      // Fetch focused artifact contents
      if (focusedArtifactIds.length > 0) {
        for (const artifactId of focusedArtifactIds) {
          try {
            // Check if it's a local artifact first
            const localArtifact = useWorkbenchStore.getState().localArtifacts.find((a) => a.id === artifactId);
            if (localArtifact && localArtifact.content) {
              const label = `Artifact: ${localArtifact.display_name}`;
              contextParts.push(`[${label}]\n${localArtifact.content}`);
              contextChunks.push({ label, preview: localArtifact.content.slice(0, 800) });
            } else {
              // Fetch from API
              const previewRes = await authFetch(`${API_BASE_URL}/api/v1/artifacts/${artifactId}/preview`);
              if (previewRes.ok) {
                const preview = await previewRes.json();
                // API returns 'text' field, not 'content'
                const previewContent = preview.text || preview.content;
                if (previewContent) {
                  // Also fetch artifact metadata for display_name
                  const metaRes = await authFetch(`${API_BASE_URL}/api/v1/artifacts/${artifactId}`);
                  const meta = metaRes.ok ? await metaRes.json() : null;
                  const displayName = meta?.display_name || artifactId;
                  const label = `Artifact: ${displayName}`;
                  contextParts.push(`[${label}]\n${previewContent}`);
                  contextChunks.push({ label, preview: String(previewContent).slice(0, 800) });
                }
              }
            }
          } catch (e) {
            console.error(`Failed to fetch artifact ${artifactId}:`, e);
          }
        }
      }

      // Add text selections
      if (textSelections.length > 0) {
        for (const sel of textSelections) {
          const label = `Selection: ${sel.artifactName} (lines ${sel.startLine}-${sel.endLine})`;
          contextParts.push(`[${label}]\n${sel.text}`);
          contextChunks.push({ label, preview: sel.text.slice(0, 800) });
        }
      }

      const contextStr = contextParts.length > 0 ? contextParts.join("\n\n---\n\n") : undefined;

      // Phase 2: Update Events panel preview with what we're about to send
      setOutboundPreview({
        persona_id: selectedPersonaId,
        user_message: content,
        context_chunks: contextChunks,
      });

      if (chatMode === "xiaolei") {
        // Phase 4: Parse artifact blocks emitted via token stream
        let parseMode: "normal" | "artifact" = "normal";
        let tokenBuf = "";
        let artifactFilename = "";
        let artifactContent = "";

        const startRe = /<<<ARTIFACT:([^>]+)>>>/;
        const endMarker = "<<<END_ARTIFACT>>>";

        const flushNormal = (text: string) => {
          if (text) appendToStreamingMessage(runId, text);
        };

        const handleArtifactComplete = async (filename: string, contentText: string) => {
          const safeName = filename.trim() || `artifact-${Date.now()}.md`;
          if (!currentSessionId) return;

          try {
            await saveArtifactMutation.mutateAsync({
              sessionId: currentSessionId,
              filename: safeName,
              content: contentText,
              artifactMeta: {
                source: "llm",
                protocol: "<<<ARTIFACT>>>",
              },
            });

            addMessage({
              id: `artifact-created-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
              session_id: currentSessionId,
              role: "assistant",
              content: `✅ Created artifact: ${safeName}`,
              created_at: new Date().toISOString(),
            });
          } catch {
            addMessage({
              id: `artifact-failed-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
              session_id: currentSessionId,
              role: "assistant",
              content: `⚠️ Failed to create artifact: ${safeName}`,
              created_at: new Date().toISOString(),
            });

            // As a fallback, show the file content inline so user doesn't lose it.
            addMessage({
              id: `artifact-content-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
              session_id: currentSessionId,
              role: "assistant",
              content: `Artifact: ${safeName}\n\n${contentText}`,
              created_at: new Date().toISOString(),
            });
          }
        };

        const onParsedToken = (t: string) => {
          tokenBuf += t;

          while (tokenBuf.length) {
            if (parseMode === "normal") {
              const m = tokenBuf.match(startRe);
              if (!m) {
                flushNormal(tokenBuf);
                tokenBuf = "";
                return;
              }

              const idx = tokenBuf.indexOf(m[0]);
              flushNormal(tokenBuf.slice(0, idx));

              artifactFilename = (m[1] || "").trim();
              tokenBuf = tokenBuf.slice(idx + m[0].length);
              artifactContent = "";
              parseMode = "artifact";
              continue;
            }

            // artifact mode
            const endIdx = tokenBuf.indexOf(endMarker);
            if (endIdx === -1) {
              artifactContent += tokenBuf;
              tokenBuf = "";
              return;
            }

            artifactContent += tokenBuf.slice(0, endIdx);
            tokenBuf = tokenBuf.slice(endIdx + endMarker.length);
            const fn = artifactFilename;
            const ct = artifactContent.replace(/^\r?\n/, "").replace(/\s+$/, "");
            artifactFilename = "";
            artifactContent = "";
            parseMode = "normal";

            // fire and forget; keep parsing stream
            void handleArtifactComplete(fn, ct);
          }
        };

        // Fetch edit target artifact content if set (B1.7)
        let editTargetContent: string | undefined;
        let editTargetName: string | undefined;
        if (editTargetArtifactId) {
          try {
            const localArt = useWorkbenchStore.getState().localArtifacts.find((a) => a.id === editTargetArtifactId);
            if (localArt?.content) {
              editTargetContent = localArt.content;
              editTargetName = localArt.display_name;
            } else {
              const previewRes = await authFetch(`${API_BASE_URL}/api/v1/artifacts/${editTargetArtifactId}/preview`);
              if (previewRes.ok) {
                const preview = await previewRes.json();
                editTargetContent = preview.text || preview.content;
              }
              const metaRes = await authFetch(`${API_BASE_URL}/api/v1/artifacts/${editTargetArtifactId}`);
              if (metaRes.ok) {
                const meta = await metaRes.json();
                editTargetName = meta.display_name;
              }
            }
          } catch (e) {
            console.error("Failed to fetch edit target artifact:", e);
          }
        }

        await streamXiaoLeiChat(
          { 
            message: content,
            system_prompt: systemPrompt,
            context: contextStr,
            // Edit target (B1.7)
            edit_target_artifact_id: editTargetArtifactId || undefined,
            edit_target_artifact_name: editTargetName,
            edit_target_artifact_content: editTargetContent,
            edit_target_selections: editTargetSelections.length > 0 ? editTargetSelections : undefined,
          },
          {
            signal: controller.signal,
            onOpen: () => setSSEConnected(true),
            onToken: (token) => onParsedToken(token),
            onArtifact: (artifactContent, filename) => {
              if (!artifactContent && !filename) return;
              // Prefer persisted artifacts (Phase 4). Fall back to local if no session.
              if (currentSessionId) {
                void handleArtifactComplete(filename || `artifact-${Date.now()}.md`, artifactContent || "");
                return;
              }

              const createdAt = new Date().toISOString();
              const trimmedName = filename?.trim();
              const extension = trimmedName?.includes(".")
                ? trimmedName.split(".").pop()?.toLowerCase() ?? null
                : null;
              const previewKind: ArtifactPreviewKind = (() => {
                if (!extension) return "markdown";
                if (extension === "md" || extension === "markdown") return "markdown";
                if (
                  [
                    "ts",
                    "tsx",
                    "js",
                    "jsx",
                    "json",
                    "py",
                    "go",
                    "rs",
                    "java",
                    "c",
                    "cpp",
                    "cs",
                    "html",
                    "css",
                    "scss",
                    "yml",
                    "yaml",
                    "sh",
                    "bash",
                    "sql",
                  ].includes(extension)
                ) {
                  return "code";
                }
                return "text";
              })();
              const displayName = trimmedName || `artifact-${createdAt.replace(/[:.]/g, "-")}.md`;
              const contentBytes = new TextEncoder().encode(artifactContent || "").length;
              const artifactId = `chat-artifact-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
              const localArtifact: LocalArtifact = {
                id: artifactId,
                run_id: runId,
                session_id: currentSessionId || "local",
                display_name: displayName,
                storage_path: `chat/${artifactId}`,
                extension: extension ?? "md",
                size_bytes: contentBytes,
                content_hash: null,
                mime_type: "text/markdown",
                artifact_type: "file",
                created_at: createdAt,
                artifact_meta: { source: "chat" },
                is_deleted: false,
                can_preview: true,
                preview_kind: previewKind,
                download_url: "",
                source: "chat",
                content: artifactContent || "",
                filename: trimmedName,
              };
              addLocalArtifact(localArtifact);
              // Do not echo full artifact content into chat (it is already saved as an artifact).
              addMessage({
                id: `artifact-created-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                session_id: currentSessionId || "",
                role: "assistant",
                content: `✅ Created artifact: ${displayName}`,
                created_at: new Date().toISOString(),
              });
            },
            onDone: async () => {
              // Check if the response is an artifact_update JSON (B1.7)
              const streamingState = useWorkbenchStore.getState().streamingMessage;
              const rawContent = streamingState?.content?.trim() || "";
              
              // DEBUG: Log raw content for troubleshooting
              console.log("[onDone] rawContent length:", rawContent.length);
              console.log("[onDone] rawContent first 100 chars:", rawContent.slice(0, 100));
              console.log("[onDone] starts with {:", rawContent.startsWith("{"));
              console.log("[onDone] ends with }:", rawContent.endsWith("}"));
              
              // Try to parse as JSON artifact_update
              if (rawContent.startsWith("{") && rawContent.endsWith("}")) {
                try {
                  const parsed = JSON.parse(rawContent);
                  console.log("[onDone] Parsed JSON type:", parsed.type);
                  if (parsed.type === "artifact_update" && parsed.artifact_id && parsed.content) {
                    console.log("[onDone] artifact_update detected, updating artifact:", parsed.artifact_id);
                    // Update the artifact via API (PUT endpoint)
                    const updateRes = await authFetch(
                      `${API_BASE_URL}/api/v1/artifacts/${parsed.artifact_id}/content`,
                      {
                        method: "PUT",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ content: parsed.content }),
                      }
                    );
                    
                    console.log("[onDone] PUT response status:", updateRes.status);
                    if (updateRes.ok) {
                      // Invalidate artifact caches to trigger auto-refresh (B1.7)
                      queryClient.invalidateQueries({ queryKey: ["artifact-preview", parsed.artifact_id] });
                      queryClient.invalidateQueries({ queryKey: ["artifact", parsed.artifact_id] });
                      queryClient.invalidateQueries({ queryKey: ["session-artifacts", currentSessionId] });
                      
                      // Clear the streaming message and show success
                      useWorkbenchStore.getState().finalizeStreamingMessage(runId);
                      // Remove the JSON from messages, add success message
                      addMessage({
                        id: `artifact-updated-${Date.now()}`,
                        session_id: currentSessionId || "",
                        role: "assistant",
                        content: `✅ Updated artifact: ${editTargetName || parsed.artifact_id}`,
                        created_at: new Date().toISOString(),
                      });
                      // Clear edit target after successful update
                      setEditTarget(null);
                      clearEditTargetSelections();
                      return;
                    } else {
                      console.error("Failed to update artifact:", await updateRes.text());
                    }
                  }
                } catch {
                  // Not valid JSON, continue with normal finalization
                }
              }
              
              finalizeStreamingMessage(runId);
            },
            onError: (message) => {
              setSSEError(message);
            },
          }
        );
      } else {
        const state = useWorkbenchStore.getState();
        const res = await authFetch(`${API_BASE_URL}/api/v1/sessions/${currentSessionId}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content,
            system_prompt: systemPrompt,
            focused_artifact_ids: state.focusedArtifactIds,
            focus_mode: state.focusMode,
            artifact_scope: state.artifactScope,
            external_sources: state.externalSources,
            llm_provider: "openrouter",
            llm_model: openrouterModel || null,
            llm_strict: true,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          const t = await res.text();
          throw new Error(t || `Failed to submit message (${res.status})`);
        }
      }
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        const message = error instanceof Error ? error.message : "Failed to send message";
        setSendError(message);
        setSSEError(message);
      }
    } finally {
      if (chatMode === "xiaolei") {
        // Get the final assistant message content before finalizing
        const finalContent = useWorkbenchStore.getState().streamingMessage?.content?.trim();
        
        finalizeStreamingMessage(runId);
        setSSEConnected(false);
        
        // Save assistant message to DB for conversation history
        if (finalContent && finalContent.length > 0) {
          void saveMessageToDb("assistant", finalContent);
        }
      }
      setIsStreaming(false);
      abortRef.current = null;
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    await sendMessage(inputValue, { clearInput: true });
  };

  // Handle keyboard shortcuts (Enter to send, Shift+Enter for new line)
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as FormEvent);
    }
  };

  // Auto-resize textarea
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    // Auto-resize
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between px-2 py-1 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <div className="flex items-center gap-1.5">
          <MessageSquare className="h-4 w-4 text-gray-600 dark:text-gray-300" />
          <span className="text-[11px] font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wide">AI</span>
        </div>
        <div className="flex items-center gap-1.5">
          {/* Chat mode */}
          <select
            value={chatMode}
            onChange={(e) => setChatMode(e.target.value as "xiaolei" | "openrouter")}
            className="text-[11px] border border-gray-300 dark:border-gray-600 rounded px-1.5 py-0.5 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
            title="Chat provider"
          >
            <option value="xiaolei">小蕾 (Lily)</option>
            <option value="openrouter">OpenRouter</option>
          </select>

          {/* OpenRouter model */}
          {chatMode === "openrouter" && (
            <select
              value={openrouterModel}
              onChange={(e) => setOpenrouterModel(e.target.value)}
              className="text-[11px] border border-gray-300 dark:border-gray-600 rounded px-1.5 py-0.5 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100"
              title="OpenRouter model"
            >
              {openrouterModels.length === 0 ? (
                <option value="">(no models configured)</option>
              ) : (
                openrouterModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name ? `${m.name} — ${m.id}` : m.id}
                  </option>
                ))
              )}
            </select>
          )}

          {/* STOP button - only show when streaming */}
          {isStreaming && (
            <button
              onClick={() => {
                if (abortRef.current) {
                  abortRef.current.abort();
                  abortRef.current = null;
                }
              }}
              className="flex items-center gap-1 px-2 py-0.5 bg-red-500 hover:bg-red-600 text-white text-[11px] font-medium rounded transition-colors"
              title="Stop generation"
            >
              <Square className="h-3 w-3 fill-current" />
              <span>STOP</span>
            </button>
          )}

          {/* Collapse button */}
          {onCollapse && (
            <button
              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
              title="Collapse panel"
              onClick={onCollapse}
            >
              <ChevronRight className="h-4 w-4 text-gray-600 dark:text-gray-300" />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 space-y-4 relative bg-white dark:bg-gray-900"
      >
        {/* Empty state */}
        {messages.length === 0 && !streamingMessage && (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <MessageSquare className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-4" />
            <p className="text-sm text-gray-500 dark:text-gray-400">Send a message to start the conversation</p>
          </div>
        )}

        {/* Message list */}
        {messages.map((msg) => (
          <MessageBubble 
            key={msg.id} 
            role={msg.role} 
            content={msg.content}
            onSaveAsArtifact={msg.role === "assistant" ? handleSaveAsArtifact : undefined}
          />
        ))}

        {/* Streaming message */}
        {streamingMessage && (
          <MessageBubble
            role="assistant"
            content={streamingMessage.content}
            isStreaming={streamingMessage.isStreaming}
          />
        )}

        {/* Jump to latest button */}
        {showJumpButton && (
          <button
            onClick={jumpToLatest}
            className="sticky bottom-4 left-1/2 -translate-x-1/2 bg-blue-500 text-white px-3 py-1.5 rounded-full text-sm shadow-lg hover:bg-blue-600 transition-colors flex items-center gap-1 z-10"
          >
            <span>↓</span>
            <span>Jump to latest</span>
          </button>
        )}
      </div>

      {/* Context status bar */}
      {contextStats.hasContent && (
        <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-purple-50 dark:bg-purple-900/20 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-purple-700 dark:text-purple-300">
            <span className="font-medium">📎 Context:</span>
            <span>
              {focusedArtifactIds.length > 0 && `${focusedArtifactIds.length} artifact${focusedArtifactIds.length > 1 ? "s" : ""}`}
              {focusedArtifactIds.length > 0 && textSelections.length > 0 && " + "}
              {textSelections.length > 0 && `${textSelections.length} selection${textSelections.length > 1 ? "s" : ""}`}
            </span>
            {contextStats.totalChars > 0 && (
              <span className="text-purple-500 dark:text-purple-400">
                ({contextStats.formattedSize})
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={() => {
              clearTextSelections();
              clearFocusedArtifacts();
            }}
            className="text-xs text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-200"
            title="Clear all context"
          >
            Clear
          </button>
        </div>
      )}

      {/* Input form */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex-shrink-0">
        {/* Persona selector row */}
        <div className="flex items-center gap-2 mb-2">
          <PersonaSelector
            selectedPersonaId={selectedPersonaId}
            onSelect={setSelectedPersona}
            disabled={isStreaming}
          />
        </div>

        {/* Input row */}
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            value={inputValue}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="Message..."
            className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none min-h-[44px] max-h-[150px] overflow-y-auto"
            disabled={isStreaming}
            rows={1}
          />
          <Button type="submit" disabled={!inputValue.trim() || isStreaming} className="px-4 py-2 h-[44px]">
            <Send className="h-4 w-4" />
          </Button>
        </div>

        {/* Error display */}
        {(sendError || sseError) && <p className="mt-2 text-sm text-red-600">{sendError || sseError}</p>}
      </form>
    </div>
  );
}

// =============================================================================
// Message Bubble Component
// =============================================================================

interface MessageBubbleProps {
  role: "user" | "assistant" | "system";
  content: string;
  isStreaming?: boolean;
  onSaveAsArtifact?: (content: string, filename: string, extension: string) => void;
}

function MessageBubble({ role, content, isStreaming, onSaveAsArtifact }: MessageBubbleProps) {
  const isUser = role === "user";
  const isAssistant = role === "assistant";
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [filename, setFilename] = useState("");
  const [extension, setExtension] = useState("md");

  const handleSave = () => {
    if (onSaveAsArtifact && filename.trim()) {
      onSaveAsArtifact(content, filename.trim(), extension);
      setShowSaveModal(false);
      setFilename("");
    }
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className="flex flex-col gap-1 max-w-[80%]">
        <div
          className={`px-4 py-2 rounded-lg ${
            isUser ? "bg-blue-500 text-white rounded-br-none" : "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-bl-none"
          }`}
        >
          <div className="whitespace-pre-wrap break-words">
            {content}
            {isStreaming && <span className="inline-block w-2 h-4 bg-current opacity-75 animate-pulse ml-0.5" />}
          </div>
        </div>
        
        {/* Save as Artifact button - only for assistant messages, not streaming */}
        {isAssistant && !isStreaming && content && (
          <button
            onClick={() => setShowSaveModal(true)}
            className="self-start flex items-center gap-1 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            title="Save as Artifact"
          >
            <FileText className="h-3 w-3" />
            Save as Artifact
          </button>
        )}

        {/* Save Modal */}
        {showSaveModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowSaveModal(false)}>
            <div className="bg-white dark:bg-gray-800 rounded-lg p-4 w-80 shadow-xl" onClick={(e) => e.stopPropagation()}>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Save as Artifact</h3>
              
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Filename
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={filename}
                      onChange={(e) => setFilename(e.target.value)}
                      placeholder="my-file"
                      className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      autoFocus
                    />
                    <select
                      value={extension}
                      onChange={(e) => setExtension(e.target.value)}
                      className="px-2 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="md">.md</option>
                      <option value="txt">.txt</option>
                      <option value="json">.json</option>
                    </select>
                  </div>
                </div>
                
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    onClick={() => setShowSaveModal(false)}
                    className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={!filename.trim()}
                    className="px-3 py-1.5 text-sm bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    Save
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
