/**
 * Console Panel Component (B2.1 - LangGraph Runtime Integration)
 *
 * Bottom-right panel - displays tool invocations, events, errors, and run history.
 *
 * Features:
 * - Real-time tool invocation display
 * - Status indicators (running, completed, failed)
 * - Error display
 * - Connection status
 * - Run history with resume support (B2.1)
 */

"use client";

import React, { useEffect, useState, useMemo, useRef } from "react";
import { Terminal, CheckCircle, XCircle, Loader2, AlertCircle, History, Brain, GitCompare, AlertTriangle, ThumbsUp, Copy, ChevronDown, MessageSquare, FileText, ScrollText } from "lucide-react";
import { Badge } from "../ui/Badge";
import { useWorkbenchStore, BrainEvent, useAuthStore } from "@/lib/store";
import { useHealth } from "@/lib/hooks/useHealth";
import { RunHistory } from "../runs/RunHistory";
import { getPersonaById } from "@/components/chat/PersonaSelector";
import { authGet } from "@/lib/api/authFetch";
import { API_BASE_URL } from "@/lib/utils/constants";

type ConsoleTab = "events" | "conversation" | "history" | "status" | "logs";

// Placeholder for conversation messages - will be populated by backend
interface ConversationMessage {
  id: string;
  role: "user" | "assistant";
  type: "message" | "artifact";
  content: string; // message text or artifact name
  timestamp: number; // epoch ms
}

interface ConsolePanelProps {
  onToggleCollapse?: () => void;
  isCollapsed?: boolean;
}

export function ConsolePanel({ onToggleCollapse }: ConsolePanelProps) {
  const { toolEvents, brainEvents, sseError, currentSessionId, selectedPersonaId, outboundPreview, editTargetArtifactId, editTargetSelections } = useWorkbenchStore();
  const [activeTab, setActiveTab] = useState<ConsoleTab>("events");

  const persona = useMemo(() => getPersonaById(selectedPersonaId), [selectedPersonaId]);

  // Merge and sort all events by timestamp (reserved for future timeline view)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const allEvents = useMemo(() => {
    const toolEventsWithType = toolEvents.map(e => ({ ...e, eventType: "tool" as const }));
    const brainEventsWithType = brainEvents.map(e => ({ ...e, eventType: "brain" as const }));
    return [...toolEventsWithType, ...brainEventsWithType].sort((a, b) => a.timestamp - b.timestamp);
  }, [toolEvents, brainEvents]);

  return (
    <div className="flex flex-col h-full bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100">
      {/* Header with tabs */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center gap-4">
          {/* Tab buttons */}
          <button
            onClick={() => setActiveTab("events")}
            className={`flex items-center gap-1.5 px-2 py-1 text-sm rounded ${
              activeTab === "events"
                ? "bg-gray-700 text-gray-100"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            <Terminal className="h-4 w-4" />
            Prompt
          </button>
          <button
            onClick={() => setActiveTab("conversation")}
            className={`flex items-center gap-1.5 px-2 py-1 text-sm rounded ${
              activeTab === "conversation"
                ? "bg-gray-700 text-gray-100"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            <MessageSquare className="h-4 w-4" />
            Conversation
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={`flex items-center gap-1.5 px-2 py-1 text-sm rounded ${
              activeTab === "history"
                ? "bg-gray-700 text-gray-100"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            <History className="h-4 w-4" />
            History
          </button>
          <button
            onClick={() => setActiveTab("status")}
            className={`flex items-center gap-1.5 px-2 py-1 text-sm rounded ${
              activeTab === "status"
                ? "bg-gray-700 text-gray-100"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            <AlertCircle className="h-4 w-4" />
            Status
          </button>
          <button
            onClick={() => setActiveTab("logs")}
            className={`flex items-center gap-1.5 px-2 py-1 text-sm rounded ${
              activeTab === "logs"
                ? "bg-gray-700 text-gray-100"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            <ScrollText className="h-4 w-4" />
            Log
          </button>
        </div>

        {/* Collapse button */}
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="p-1.5 text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded transition-colors"
            title="Collapse console"
          >
            <ChevronDown className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Tab Content */}
      {activeTab === "events" ? (
        <div className="flex-1 overflow-y-auto p-3 space-y-2 font-mono text-sm">
          {/* Phase 2: Outbound preview (system prompt/user/context) */}
          <div className="border border-gray-700/40 bg-gray-900/20 rounded p-3 space-y-2">
            <div className="text-xs text-gray-400">📤 System Prompt</div>
            <div className="text-xs text-gray-200 bg-gray-800/50 px-2 py-1 rounded whitespace-pre-wrap break-words max-h-40 overflow-auto">
              {persona.system_prompt}
            </div>

            <div className="flex items-center justify-between">
              <div className="text-xs text-gray-400">📝 User Message</div>
              {outboundPreview?.updated_at ? (
                <div className="text-[10px] text-gray-500">
                  {new Date(outboundPreview.updated_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </div>
              ) : null}
            </div>
            <div className="text-xs text-gray-200 bg-gray-800/50 px-2 py-1 rounded whitespace-pre-wrap break-words max-h-28 overflow-auto">
              {outboundPreview?.user_message || "(no message yet)"}
            </div>

            <div className="text-xs text-gray-400">📎 Context</div>
            {outboundPreview?.context_chunks?.length ? (
              <div className="space-y-2">
                {outboundPreview.context_chunks.map((c, idx) => (
                  <div key={idx} className="border border-gray-700/30 rounded p-2 bg-gray-800/30">
                    <div className="text-[11px] text-gray-300 mb-1">{c.label}</div>
                    <div className="text-xs text-gray-200 whitespace-pre-wrap break-words max-h-24 overflow-auto">
                      {c.preview}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-gray-500">(no context)</div>
            )}

            {/* Edit Target (B1.7) */}
            <div className="text-xs text-gray-400">✏️ Edit Target</div>
            {editTargetArtifactId ? (
              <div className="border border-amber-500/30 rounded p-2 bg-amber-900/20">
                <div className="text-[11px] text-amber-300 mb-1">
                  Artifact ID: <span className="font-mono">{editTargetArtifactId.slice(0, 8)}...</span>
                </div>
                {editTargetSelections.length > 0 ? (
                  <div className="space-y-1">
                    <div className="text-[10px] text-amber-400">
                      {editTargetSelections.length} section(s) selected:
                    </div>
                    {editTargetSelections.slice(0, 3).map((sel, idx) => (
                      <div key={idx} className="text-xs text-amber-200 bg-amber-800/30 px-2 py-1 rounded">
                        Lines {sel.startLine}-{sel.endLine}: {sel.text.slice(0, 60)}...
                      </div>
                    ))}
                    {editTargetSelections.length > 3 && (
                      <div className="text-[10px] text-amber-400">
                        +{editTargetSelections.length - 3} more...
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-amber-200">
                    Entire artifact will be updated
                  </div>
                )}
              </div>
            ) : (
              <div className="text-xs text-gray-500">(no edit target)</div>
            )}
          </div>
          {/* Error display */}
          {sseError && (
            <div className="bg-red-900/50 border border-red-700 text-red-200 px-3 py-2 rounded flex items-start gap-2">
              <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
              <span>{sseError}</span>
            </div>
          )}
        </div>
      ) : activeTab === "conversation" ? (
        <ConversationTab sessionId={currentSessionId} />
      ) : activeTab === "history" ? (
        <div className="flex-1 overflow-hidden">
          <RunHistory sessionId={currentSessionId} />
        </div>
      ) : activeTab === "logs" ? (
        <div className="flex-1 overflow-hidden">
          <LogTab />
        </div>
      ) : (
        <StatusTab />
      )}
    </div>
  );
}

// =============================================================================
// Tool Event Card Component
// =============================================================================

interface ToolEventCardProps {
  event: {
    tool_call_id: string;
    tool_name: string;
    input_preview: string;
    status: "running" | "completed" | "failed";
    output_preview?: string;
    exit_code?: number;
    duration_ms?: number;
    timestamp: number;
  };
}

// =============================================================================
// Conversation Tab Component (with AI output context menu)
// =============================================================================

interface ConversationTabProps {
  sessionId: string | null;
}

interface AIContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  selectedText: string;
}

function ConversationTab({ sessionId }: ConversationTabProps) {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const refreshToken = useWorkbenchStore((s) => s.conversationRefreshToken);
  
  // Context menu state
  const [contextMenu, setContextMenu] = useState<AIContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    selectedText: "",
  });
  
  // Create artifact modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createArtifactName, setCreateArtifactName] = useState("");
  const [createArtifactContent, setCreateArtifactContent] = useState("");
  
  // Get store state for edit target
  const editTargetArtifactId = useWorkbenchStore((s) => s.editTargetArtifactId);
  const setArtifactFlash = useWorkbenchStore((s) => s.setArtifactFlash);

  useEffect(() => {
    if (!sessionId) return;

    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const resp = await authGet(`${API_BASE_URL}/api/v1/sessions/${sessionId}/conversation`);
        if (!resp.ok) {
          const text = await resp.text();
          throw new Error(text || `HTTP ${resp.status}`);
        }
        const data = (await resp.json()) as {
          messages: Array<{
            id: string;
            role: "user" | "assistant" | "system";
            type: "message" | "artifact";
            content: string;
            timestamp: string;
          }>;
        };

        if (cancelled) return;
        const mapped = (data.messages || []).map((m) => ({
          id: m.id,
          role: m.role === "system" ? "assistant" : m.role,
          type: m.type,
          content: m.content,
          timestamp: new Date(m.timestamp).getTime(),
        }));
        setMessages(mapped);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : String(e));
        setMessages([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [sessionId, refreshToken]);
  
  // Handle right-click on AI messages
  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    const selection = window.getSelection();
    const selectedText = selection?.toString() || "";
    
    if (selectedText) {
      setContextMenu({
        visible: true,
        x: e.clientX,
        y: e.clientY,
        selectedText,
      });
    }
  };
  
  // Close context menu
  const closeContextMenu = () => {
    setContextMenu((prev) => ({ ...prev, visible: false }));
  };
  
  // Close on click outside
  useEffect(() => {
    const handleClick = () => closeContextMenu();
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);
  
  // Create new artifact from selection
  const handleCreateArtifact = () => {
    const words = contextMenu.selectedText.trim().split(/\s+/).slice(0, 5).join("_");
    const suggestedName = words.replace(/[^a-zA-Z0-9_-]/g, "").substring(0, 30) || "ai_output";
    setCreateArtifactName(suggestedName);
    setCreateArtifactContent(contextMenu.selectedText);
    setShowCreateModal(true);
    closeContextMenu();
  };
  
  // Append to edit target artifact
  const handleAppendToArtifact = async () => {
    if (!editTargetArtifactId || !contextMenu.selectedText) return;
    
    try {
      // Fetch current content
      const resp = await authGet(`${API_BASE_URL}/api/v1/artifacts/${editTargetArtifactId}/preview`);
      if (!resp.ok) throw new Error("Failed to fetch artifact");
      const data = await resp.json();
      // API may return text OR content field
      const currentContent = data.text || data.content || "";
      
      console.log("[Append] Current content length:", currentContent.length);
      console.log("[Append] Selected text length:", contextMenu.selectedText.length);
      
      // Append new content
      const newContent = currentContent + "\n\n" + contextMenu.selectedText;
      
      console.log("[Append] New content length:", newContent.length);
      
      // Update artifact using fetch with PUT method
      const updateResp = await fetch(`${API_BASE_URL}/api/v1/artifacts/${editTargetArtifactId}/content`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: newContent }),
      });
      
      if (!updateResp.ok) {
        const errText = await updateResp.text();
        throw new Error(`Failed to update artifact: ${errText}`);
      }
      
      // Flash feedback
      setArtifactFlash(editTargetArtifactId);
      setTimeout(() => setArtifactFlash(null), 1000);
      
      console.log("[Append] Success!");
    } catch (err) {
      console.error("Failed to append to artifact:", err);
    }
    
    closeContextMenu();
  };
  
  // Context menu item component
  const MenuItem = ({
    label,
    onClick,
    disabled,
    icon,
  }: {
    label: string;
    onClick: () => void;
    disabled?: boolean;
    icon?: React.ReactNode;
  }) => (
    <div
      onClick={(e) => {
        e.stopPropagation();
        if (!disabled) onClick();
      }}
      className={`flex items-center gap-2 px-3 py-1.5 text-sm cursor-pointer transition-colors ${
        disabled
          ? "text-gray-500 cursor-not-allowed"
          : "text-gray-200 hover:bg-gray-700"
      }`}
    >
      {icon}
      <span>{label}</span>
    </div>
  );

  if (!sessionId) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <p className="text-sm text-gray-500">Select a session to view conversation</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <p className="text-sm text-gray-500">Loading…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <p className="text-sm text-red-500">Failed to load conversation: {error}</p>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-4">
        <p className="text-sm text-gray-500">No messages yet</p>
      </div>
    );
  }

  return (
    <>
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex gap-2 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-700 text-gray-100"
              }`}
              onContextMenu={msg.role === "assistant" ? handleContextMenu : undefined}
            >
              {msg.type === "artifact" ? (
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  <span className="font-medium">{msg.content}</span>
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              )}
              <div className="text-[10px] opacity-70 mt-1">
                {new Date(msg.timestamp).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </div>
            </div>
          </div>
        ))}
      </div>
      
      {/* AI Output Context Menu */}
      {contextMenu.visible && (
        <div
          className="fixed z-50 bg-gray-800 rounded-lg shadow-lg border border-gray-700 py-1 min-w-[200px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <MenuItem
            label="📄 Create Artifact"
            onClick={handleCreateArtifact}
            disabled={!contextMenu.selectedText}
          />
          <MenuItem
            label="➕ Append to Artifact"
            onClick={handleAppendToArtifact}
            disabled={!contextMenu.selectedText || !editTargetArtifactId}
          />
          <div className="border-t border-gray-700 my-1" />
          <MenuItem
            label="📋 Copy"
            onClick={() => {
              navigator.clipboard.writeText(contextMenu.selectedText);
              closeContextMenu();
            }}
            disabled={!contextMenu.selectedText}
          />
        </div>
      )}
      
      {/* Create Artifact Modal */}
      {showCreateModal && (
        <>
          <div className="fixed inset-0 bg-black/50 z-50" onClick={() => setShowCreateModal(false)} />
          <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-gray-800 rounded-lg shadow-xl p-4 z-50 w-96 max-h-[80vh] overflow-auto">
            <h3 className="text-lg font-semibold mb-3 text-white">Create New Artifact</h3>
            <input
              type="text"
              value={createArtifactName}
              onChange={(e) => setCreateArtifactName(e.target.value)}
              placeholder="Artifact name"
              className="w-full px-3 py-2 border border-gray-600 rounded-lg bg-gray-700 text-white mb-3"
              autoFocus
            />
            <textarea
              value={createArtifactContent}
              onChange={(e) => setCreateArtifactContent(e.target.value)}
              placeholder="Content"
              className="w-full px-3 py-2 border border-gray-600 rounded-lg bg-gray-700 text-white mb-3 h-40 resize-none"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-3 py-1.5 text-sm text-gray-300 hover:bg-gray-700 rounded"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  if (!sessionId || !createArtifactName) return;
                  try {
                    const resp = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/artifacts`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({
                        display_name: createArtifactName + ".md",
                        content: createArtifactContent,
                      }),
                    });
                    if (!resp.ok) throw new Error("Failed to create artifact");
                    setShowCreateModal(false);
                    setCreateArtifactName("");
                    setCreateArtifactContent("");
                  } catch (err) {
                    console.error("Failed to create artifact:", err);
                  }
                }}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Create
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
}

// =============================================================================
// Status Tab Component
// =============================================================================

function StatusTab() {
  const { authStatus } = useAuthStore();
  const { data, isLoading, isError } = useHealth();
  const sseError = useWorkbenchStore((s) => s.sseError);

  const healthLabel = isLoading
    ? "Checking"
    : isError
    ? "Offline"
    : data?.status || "unknown";

  return (
    <div className="flex-1 overflow-y-auto p-4 text-sm">
      <div className="space-y-2">
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-2">
          <span className="text-gray-600 dark:text-gray-300">Backend</span>
          <span className="text-gray-900 dark:text-gray-100">{healthLabel}</span>
        </div>
        <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 pb-2">
          <span className="text-gray-600 dark:text-gray-300">Auth</span>
          <span className="text-gray-900 dark:text-gray-100">{authStatus}</span>
        </div>
        {/* Phase 3: Removed noisy live connection indicator */}
        {sseError && (
          <div className="mt-3 p-3 rounded border border-amber-300/40 bg-amber-900/10 text-amber-200">
            <div className="font-medium mb-1">Notice</div>
            <div className="text-xs">{sseError}</div>
          </div>
        )}
        {authStatus === "disabled" && (
          <div className="mt-3 p-3 rounded border border-yellow-300/40 bg-yellow-900/10 text-yellow-200">
            <div className="font-medium mb-1">Auth not available</div>
            <div className="text-xs">Authentication is disabled on the backend. Some features (like API key management) are hidden.</div>
          </div>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Log Tab Component (Real-time log streaming)
// =============================================================================

interface LogEntry {
  timestamp: string;
  level: string;
  component: string;
  message: string;
  extra?: Record<string, unknown>;
}

function LogTab() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [levelFilter, setLevelFilter] = useState<string>("ALL");
  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Connect to WebSocket log stream
  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//localhost:8001/api/v1/logs/stream`;
    
    let ws: WebSocket;
    let reconnectTimer: NodeJS.Timeout;

    function connect() {
      ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "ping") return; // Ignore keepalive
          setLogs((prev) => [...prev.slice(-499), data]); // Keep last 500
        } catch {
          // Ignore parse errors
        }
      };

      ws.onerror = () => {
        setError("WebSocket connection error");
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        // Reconnect after 3 seconds
        reconnectTimer = setTimeout(connect, 3000);
      };
    }

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Filter logs by level
  const filteredLogs = levelFilter === "ALL" 
    ? logs 
    : logs.filter(l => l.level === levelFilter);

  const levelColor = (level: string) => {
    switch (level) {
      case "DEBUG": return "text-gray-400";
      case "INFO": return "text-blue-400";
      case "WARNING": return "text-yellow-400";
      case "ERROR": return "text-red-400";
      case "CRITICAL": return "text-red-600 font-bold";
      default: return "text-gray-300";
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-green-500" : "bg-red-500"}`} />
          <span className="text-xs text-gray-400">
            {connected ? "Connected" : "Disconnected"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="text-xs bg-gray-800 text-gray-300 border border-gray-600 rounded px-2 py-1"
          >
            <option value="ALL">All Levels</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>
          <button
            onClick={() => setLogs([])}
            className="text-xs text-gray-400 hover:text-gray-200 px-2 py-1"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Log entries */}
      <div className="flex-1 overflow-y-auto p-2 font-mono text-xs space-y-0.5">
        {error && (
          <div className="text-red-400 py-1">{error}</div>
        )}
        {filteredLogs.length === 0 ? (
          <div className="text-gray-500 py-4 text-center">
            {connected ? "Waiting for logs..." : "Connecting..."}
          </div>
        ) : (
          filteredLogs.map((log, idx) => (
            <div key={idx} className="flex gap-2 hover:bg-gray-800/50 py-0.5 px-1 rounded">
              <span className="text-gray-500 flex-shrink-0">
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
              <span className={`flex-shrink-0 w-16 ${levelColor(log.level)}`}>
                [{log.level}]
              </span>
              <span className="text-purple-400 flex-shrink-0 max-w-32 truncate">
                {log.component}
              </span>
              <span className="text-gray-200 break-all">
                {log.message}
              </span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  );
}

async function copyToClipboard(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    return;
  } catch {
    // fallback
  }

  try {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.top = "-9999px";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
  } catch {
    // ignore
  }
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function ToolEventCard({ event }: ToolEventCardProps) {
  const [expanded, setExpanded] = useState(false);

  const statusStyles = {
    running: "border-yellow-500/50 bg-yellow-900/20",
    completed: "border-green-500/50 bg-green-900/20",
    failed: "border-red-500/50 bg-red-900/20",
  };

  const StatusIcon = {
    running: <Loader2 className="h-4 w-4 text-yellow-400 animate-spin" />,
    completed: <CheckCircle className="h-4 w-4 text-green-400" />,
    failed: <XCircle className="h-4 w-4 text-red-400" />,
  }[event.status];

  // Best-effort parsing of tool input preview (esp. shell_exec)
  let parsed: unknown = null;
  try {
    parsed = JSON.parse(event.input_preview) as unknown;
  } catch {
    // ignore
  }

  const shellCommandSummary = (() => {
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return null;
    const p = parsed as Record<string, unknown>;
    const command = typeof p.command === "string" ? p.command : null;
    const cwd = typeof p.cwd === "string" ? p.cwd : null;
    if (!command && !cwd) return null;
    return `${command ?? ""}${cwd ? `  (cwd: ${cwd})` : ""}`.trim();
  })();

  const timeLabel = new Date(event.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div className={`p-3 rounded border ${statusStyles[event.status]} transition-colors`}>
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-start gap-2 min-w-0">
          <div className="mt-0.5">{StatusIcon}</div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-200 truncate">{event.tool_name}</span>
              <span className="text-[10px] text-gray-500">{timeLabel}</span>
            </div>
            {shellCommandSummary && (
              <div className="text-[11px] text-gray-300 truncate">{shellCommandSummary}</div>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusBadge event={event} />

          <button
            type="button"
            className="inline-flex items-center gap-1 text-[11px] text-gray-400 hover:text-gray-200"
            title="Copy input"
            onClick={() => copyToClipboard(event.input_preview)}
          >
            <Copy className="h-3.5 w-3.5" />
            In
          </button>

          {event.output_preview && (
            <button
              type="button"
              className="inline-flex items-center gap-1 text-[11px] text-gray-400 hover:text-gray-200"
              title="Copy output"
              onClick={() => copyToClipboard(event.output_preview || "")}
            >
              <Copy className="h-3.5 w-3.5" />
              Out
            </button>
          )}

          <button
            type="button"
            className="text-[11px] text-gray-400 hover:text-gray-200"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? "Collapse" : "Expand"}
          </button>
        </div>
      </div>

      {/* Input preview */}
      <div className="text-xs text-gray-400 mb-1">Input:</div>
      <div
        className={
          expanded
            ? "text-xs text-gray-300 bg-gray-800/50 px-2 py-1 rounded whitespace-pre-wrap break-words max-h-48 overflow-auto mb-2"
            : "text-xs text-gray-300 bg-gray-800/50 px-2 py-1 rounded truncate mb-2"
        }
      >
        {event.input_preview}
      </div>

      {/* Output preview (if completed/failed) */}
      {event.output_preview && (
        <>
          <div className="text-xs text-gray-400 mb-1">Output:</div>
          <div
            className={
              expanded
                ? "text-xs text-gray-300 bg-gray-800/50 px-2 py-1 rounded whitespace-pre-wrap break-words max-h-48 overflow-auto"
                : "text-xs text-gray-300 bg-gray-800/50 px-2 py-1 rounded truncate"
            }
          >
            {event.output_preview}
          </div>
        </>
      )}
    </div>
  );
}

// =============================================================================
// Brain Event Card Component (B2.2)
// =============================================================================

interface BrainEventCardProps {
  event: BrainEvent;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
function BrainEventCard({ event }: BrainEventCardProps) {
  const data = event.data as Record<string, unknown>;

  // Style and content based on event type
  const config = {
    classification: {
      icon: <Brain className="h-4 w-4 text-blue-400" />,
      label: "Classification",
      borderColor: "border-blue-500/50",
      bgColor: "bg-blue-900/20",
      render: () => {
        const complexity = data.complexity as string;
        const mode = data.mode as string;
        const reasonCode = data.reason_code as string;
        const brainModel = data.brain_model as string;
        return (
          <div className="space-y-1">
            <div className="flex gap-2">
              <Badge variant={complexity === "simple" ? "success" : "warning"} size="sm">
                {complexity}
              </Badge>
              <Badge variant="default" size="sm">{mode}</Badge>
              <Badge variant="default" size="sm">{reasonCode}</Badge>
            </div>
            {brainModel && (
              <div className="text-xs text-gray-500">via {brainModel}</div>
            )}
          </div>
        );
      },
    },
    brain_thinking: {
      icon: <Brain className="h-4 w-4 text-purple-400" />,
      label: `${(data.brain as string) || "Brain"} Thinking`,
      borderColor: "border-purple-500/50",
      bgColor: "bg-purple-900/20",
      render: () => {
        const decision = data.decision as Record<string, unknown>;
        const toolName = decision?.tool_name as string | null;
        const summary = decision?.summary as string | null;
        const brainModel = data.brain_model as string;
        return (
          <div className="space-y-1">
            <div className="flex gap-2 flex-wrap items-center">
              <Badge variant="default" size="sm">{decision?.intent as string}</Badge>
              {toolName && (
                <Badge variant="warning" size="sm">🔧 {toolName}</Badge>
              )}
            </div>
            {brainModel && (
              <div className="text-xs text-gray-500">via {brainModel}</div>
            )}
            {summary && (
              <div className="text-xs text-gray-400 line-clamp-2">{summary}</div>
            )}
          </div>
        );
      },
    },
    deliberation_round: {
      icon: <GitCompare className="h-4 w-4 text-cyan-400" />,
      label: `Deliberation Round ${data.round_display}/${data.max_rounds}`,
      borderColor: "border-cyan-500/50",
      bgColor: "bg-cyan-900/20",
      render: () => {
        const b1 = data.b1_decision as Record<string, unknown>;
        const b2 = data.b2_decision as Record<string, unknown>;
        const match = b1?.intent === b2?.intent;
        return (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">B1:</span>
              <Badge variant="default" size="sm">{b1?.intent as string}</Badge>
              <span className="text-xs text-gray-500">B2:</span>
              <Badge variant="default" size="sm">{b2?.intent as string}</Badge>
              {match ? (
                <CheckCircle className="h-3 w-3 text-green-400" />
              ) : (
                <XCircle className="h-3 w-3 text-red-400" />
              )}
            </div>
          </div>
        );
      },
    },
    consensus_reached: {
      icon: <ThumbsUp className="h-4 w-4 text-green-400" />,
      label: "Consensus Reached",
      borderColor: "border-green-500/50",
      bgColor: "bg-green-900/20",
      render: () => {
        const artifacts = data.target_artifacts as string[];
        return (
          <div className="flex gap-2 items-center">
            <Badge variant="success" size="sm">{data.intent as string}</Badge>
            {artifacts?.length > 0 && (
              <span className="text-xs text-gray-400">→ {artifacts.join(", ")}</span>
            )}
          </div>
        );
      },
    },
    consensus_failed: {
      icon: <XCircle className="h-4 w-4 text-orange-400" />,
      label: "Consensus Failed",
      borderColor: "border-orange-500/50",
      bgColor: "bg-orange-900/20",
      render: () => (
        <div className="text-xs text-orange-300">
          After {data.rounds as number} rounds: {data.reason as string}
        </div>
      ),
    },
    escalation_required: {
      icon: <AlertTriangle className="h-4 w-4 text-red-400" />,
      label: "⚠️ Escalation Required",
      borderColor: "border-red-500/50",
      bgColor: "bg-red-900/20",
      render: () => (
        <div className="space-y-1">
          <div className="text-xs text-red-300 font-medium">
            Needs human decision ({data.reason as string})
          </div>
          <div className="text-xs text-gray-400">
            After {data.rounds_attempted as number} rounds
          </div>
        </div>
      ),
    },
  };

  const eventConfig = config[event.type as keyof typeof config] || {
    icon: <Terminal className="h-4 w-4 text-gray-400" />,
    label: event.type,
    borderColor: "border-gray-500/50",
    bgColor: "bg-gray-900/20",
    render: () => <pre className="text-xs overflow-auto">{JSON.stringify(data, null, 2)}</pre>,
  };

  return (
    <div className={`p-3 rounded border ${eventConfig.borderColor} ${eventConfig.bgColor} transition-colors`}>
      <div className="flex items-center gap-2 mb-2">
        {eventConfig.icon}
        <span className="font-medium text-gray-200 text-sm">{eventConfig.label}</span>
      </div>
      {eventConfig.render()}
    </div>
  );
}

// =============================================================================
// Status Badge Component
// =============================================================================

function formatDuration(ms?: number) {
  if (ms == null) return "";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const s = Math.round(ms / 1000);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}m ${r}s`;
}

function StatusBadge({ event }: ToolEventCardProps) {
  if (event.status === "running") {
    return <span className="text-xs text-yellow-400">Running…</span>;
  }

  const dur = formatDuration(event.duration_ms);
  const exit = event.exit_code;

  if (event.status === "completed") {
    return (
      <span className="text-xs text-green-400">
        ✓{exit != null ? ` Exit ${exit}` : ""}{dur ? ` • ${dur}` : ""}
      </span>
    );
  }

  if (event.status === "failed") {
    return (
      <span className="text-xs text-red-400">
        ✗{exit != null ? ` Exit ${exit}` : " Failed"}{dur ? ` • ${dur}` : ""}
      </span>
    );
  }

  return null;
}
