/**
 * Workbench Layout Component
 *
 * VS Code-style IDE layout using react-resizable-panels.
 *
 * Layout:
 * ┌─────────────────────────────────────────────────┐
 * │                  (Toolbar in page.tsx)          │
 * ├────────┬────────────────────────────┬───────────┤
 * │        │  [Session Tabs]            │           │
 * │Explorer├────────────────────────────┤   Chat    │
 * │ (250px)│       Main Editor          │  (350px)  │
 * │        │      (ArtifactsPanel)      │           │
 * │        │                            │           │
 * │        ├────────────────────────────┤           │
 * │        │     Terminal/Console       │           │
 * │        │      (collapsible)         │           │
 * └────────┴────────────────────────────┴───────────┘
 */

"use client";

import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Panel,
  PanelGroup,
  PanelResizeHandle,
  type ImperativePanelHandle,
} from "react-resizable-panels";
import {
  ChevronDown,
  ChevronUp,
  Terminal,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { ExplorerPanel } from "./ExplorerPanel";
import { ReasoningPanel } from "./ReasoningPanel";
import { ArtifactsPanel } from "./ArtifactsPanel";
import { ConsolePanel } from "./ConsolePanel";
import { SessionTabBar, type Session } from "@/components/sessions/SessionTabBar";
import { useSessions, useCreateSession, useUpdateSession, useDeleteSession } from "@/lib/hooks/useSessions";
import { useQueryClient } from "@tanstack/react-query";
import { useWorkbenchStore } from "@/lib/store";
import { cn } from "@/lib/utils/cn";
import { API_BASE_URL } from "@/lib/utils/constants";
import { getAuthenticatedSSEUrl } from "@/lib/api/authFetch";
import { useArtifactCacheHelpers } from "@/lib/hooks/useArtifacts";

// Local storage key for session order
const SESSION_ORDER_KEY = "agent-b-session-order";

export function WorkbenchLayout() {
  // IDE-style defaults: slim sidebars + slim bottom bar + big editor
  const [isTerminalOpen, setIsTerminalOpen] = useState(true);
  const [terminalSize, setTerminalSize] = useState(20);
  const [orderedSessions, setOrderedSessions] = useState<Session[]>([]);

  // Collapsible panels
  const explorerPanelRef = useRef<ImperativePanelHandle>(null);
  const chatPanelRef = useRef<ImperativePanelHandle>(null);
  const [isExplorerCollapsed, setIsExplorerCollapsed] = useState(false);
  const [isChatCollapsed, setIsChatCollapsed] = useState(false);
  const [isSessionBarCollapsed, setIsSessionBarCollapsed] = useState(false);

  // Session data and mutations
  const { data: sessions = [] } = useSessions();
  const createSession = useCreateSession();
  const updateSession = useUpdateSession();
  const deleteSession = useDeleteSession();
  
  // Current session from store
  const currentSessionId = useWorkbenchStore((s) => s.currentSessionId);
  const setCurrentSession = useWorkbenchStore((s) => s.setCurrentSession);
  
  // Editor maximize state
  const isEditorMaximized = useWorkbenchStore((s) => s.isEditorMaximized);

  // Stage 10: SSE connection
  const queryClient = useQueryClient();
  const artifactCache = useArtifactCacheHelpers();
  const setSSEConnected = useWorkbenchStore((s) => s.setSSEConnected);
  const setSSEError = useWorkbenchStore((s) => s.setSSEError);
  const appendToStreamingMessage = useWorkbenchStore((s) => s.appendToStreamingMessage);
  const finalizeStreamingMessage = useWorkbenchStore((s) => s.finalizeStreamingMessage);
  const addToolEvent = useWorkbenchStore((s) => s.addToolEvent);
  const updateToolEvent = useWorkbenchStore((s) => s.updateToolEvent);
  const markRunningToolsAsFailed = useWorkbenchStore((s) => s.markRunningToolsAsFailed);
  const markCompleted = useWorkbenchStore((s) => s.markCompleted);
  const markFailed = useWorkbenchStore((s) => s.markFailed);
  const setActiveRun = useWorkbenchStore((s) => s.setActiveRun);
  const bumpConversationRefresh = useWorkbenchStore((s) => s.bumpConversationRefresh);

  // Handle editor maximize state - collapse/expand all panels
  useEffect(() => {
    // Use setTimeout to ensure panel refs are ready
    const timer = setTimeout(() => {
      if (isEditorMaximized) {
        // Collapse all panels
        explorerPanelRef.current?.collapse();
        chatPanelRef.current?.collapse();
        setIsTerminalOpen(false);
        setIsSessionBarCollapsed(true);
        setIsExplorerCollapsed(true);
        setIsChatCollapsed(true);
      } else {
        // Restore panels
        explorerPanelRef.current?.expand(12);
        chatPanelRef.current?.expand(22);
        setIsTerminalOpen(true);
        setIsSessionBarCollapsed(false);
        setIsExplorerCollapsed(false);
        setIsChatCollapsed(false);
      }
    }, 50);
    return () => clearTimeout(timer);
  }, [isEditorMaximized]);

  // Load session order from localStorage and merge with fetched sessions
  useEffect(() => {
    if (sessions.length === 0) {
      setOrderedSessions([]);
      return;
    }

    // Get saved order from localStorage
    const savedOrder = localStorage.getItem(SESSION_ORDER_KEY);
    const orderIds: string[] = savedOrder ? JSON.parse(savedOrder) : [];

    // Sort sessions: ordered ones first, then new ones
    const sessionMap = new Map(sessions.map(s => [s.id, s]));
    const ordered: Session[] = [];
    
    // Add sessions in saved order
    for (const id of orderIds) {
      const session = sessionMap.get(id);
      if (session) {
        ordered.push(session);
        sessionMap.delete(id);
      }
    }
    
    // Add remaining sessions (new ones)
    for (const session of sessionMap.values()) {
      ordered.push(session);
    }

    setOrderedSessions(ordered);

    // Auto-select first session if none selected
    if (!currentSessionId && ordered.length > 0) {
      setCurrentSession(ordered[0].id);
    }
  }, [sessions, currentSessionId, setCurrentSession]);

  // Stage 10: connect SSE stream for current session
  useEffect(() => {
    if (!currentSessionId) return;

    const url = getAuthenticatedSSEUrl(
      `${API_BASE_URL}/api/v1/sessions/${currentSessionId}/stream`
    );

    const es = new EventSource(url);
    setSSEConnected(false);

    es.onopen = () => {
      setSSEConnected(true);
      setSSEError(null);
    };

    es.onerror = () => {
      // EventSource will auto-retry; we just reflect state.
      setSSEConnected(false);
      setSSEError("SSE disconnected (auto-retrying)");
    };

    const onToken = (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      appendToStreamingMessage(data.run_id, data.content);
      setActiveRun(data.run_id);
    };

    const onToolStart = (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      addToolEvent({
        tool_call_id: data.tool_call_id,
        tool_name: data.tool_name,
        input_preview: data.input_preview,
        status: "running",
      });
    };

    const onToolEnd = (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      updateToolEvent(data.tool_call_id, {
        status: data.exit_code === 0 ? "completed" : "failed",
        exit_code: data.exit_code,
        output_preview: data.output_preview,
        duration_ms: data.duration_ms,
      });
    };

    const onErrorEvent = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        setSSEError(data.message || "Error");
      } catch {
        setSSEError("Error");
      }
    };

    const onDone = (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      finalizeStreamingMessage(data.run_id);
      markCompleted();
    };

    const onRunTerminated = (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      markRunningToolsAsFailed(`Terminated: ${data.reason || "user_cancel"}`);
    };

    const onArtifactCreated = (e: MessageEvent) => {
      // Prefer incremental cache update; fallback to invalidation.
      try {
        const data = JSON.parse(e.data);
        const artifact = data?.artifact;
        if (artifact?.id && artifact?.session_id) {
          artifactCache.addArtifact(artifact);
          bumpConversationRefresh();
          return;
        }
      } catch {
        // ignore
      }

      queryClient.invalidateQueries({
        queryKey: ["session-artifacts", currentSessionId],
      });
      bumpConversationRefresh();
    };

    const onArtifactDeleted = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        if (data?.artifact_id && data?.session_id && data?.run_id) {
          artifactCache.removeArtifact({
            artifactId: data.artifact_id,
            sessionId: data.session_id,
            runId: data.run_id,
          });
          return;
        }
      } catch {
        // ignore
      }

      queryClient.invalidateQueries({
        queryKey: ["session-artifacts", currentSessionId],
      });
      bumpConversationRefresh();
    };

    const onRunStateChanged = (e: MessageEvent) => {
      const data = JSON.parse(e.data);
      if (data.status === "running") {
        setActiveRun(data.run_id);
      } else if (data.status === "completed") {
        markCompleted();
      } else if (data.status === "failed") {
        markFailed(data.error || "Run failed");
      }
    };

    es.addEventListener("token", onToken);
    es.addEventListener("tool_start", onToolStart);
    es.addEventListener("tool_end", onToolEnd);
    es.addEventListener("error", onErrorEvent);
    es.addEventListener("done", onDone);
    es.addEventListener("run_terminated", onRunTerminated);
    es.addEventListener("artifact_created", onArtifactCreated);
    es.addEventListener("artifact_deleted", onArtifactDeleted);
    es.addEventListener("run_state_changed", onRunStateChanged);

    return () => {
      es.close();
      setSSEConnected(false);
    };
  }, [
    currentSessionId,
    queryClient,
    setSSEConnected,
    setSSEError,
    appendToStreamingMessage,
    finalizeStreamingMessage,
    addToolEvent,
    updateToolEvent,
    markRunningToolsAsFailed,
    markCompleted,
    markFailed,
    setActiveRun,
    artifactCache,
  ]);

  // Save session order to localStorage
  const saveSessionOrder = useCallback((newOrder: Session[]) => {
    const orderIds = newOrder.map(s => s.id);
    localStorage.setItem(SESSION_ORDER_KEY, JSON.stringify(orderIds));
  }, []);

  const handleSessionSelect = useCallback((sessionId: string) => {
    setCurrentSession(sessionId);
  }, [setCurrentSession]);

  const handleSessionCreate = useCallback(async () => {
    const title = `Session ${orderedSessions.length + 1}`;
    await createSession.mutateAsync({ title });
  }, [createSession, orderedSessions.length]);

  const handleSessionRename = useCallback(async (sessionId: string, newTitle: string) => {
    await updateSession.mutateAsync({ sessionId, data: { title: newTitle } });
  }, [updateSession]);

  const handleSessionDelete = useCallback(async (sessionId: string) => {
    if (!confirm("Delete this session and all its contents?")) return;
    
    await deleteSession.mutateAsync(sessionId);
    
    // Update local order
    const newOrder = orderedSessions.filter(s => s.id !== sessionId);
    setOrderedSessions(newOrder);
    saveSessionOrder(newOrder);
    
    // Select another session if we deleted the current one
    if (currentSessionId === sessionId && newOrder.length > 0) {
      setCurrentSession(newOrder[0].id);
    }
  }, [deleteSession, orderedSessions, currentSessionId, setCurrentSession, saveSessionOrder]);

  const handleSessionReorder = useCallback((newOrder: Session[]) => {
    setOrderedSessions(newOrder);
    saveSessionOrder(newOrder);
  }, [saveSessionOrder]);

  const toggleTerminal = () => {
    setIsTerminalOpen(!isTerminalOpen);
  };

  return (
    <div className="h-full w-full overflow-hidden">
      <PanelGroup
        direction="horizontal"
        className="h-full"
        autoSaveId="workbench-layout:v1"
      >
        {/* Left Panel: Explorer (collapsible) */}
        <Panel
          ref={explorerPanelRef}
          defaultSize={12}
          minSize={10}
          maxSize={50}
          collapsible
          collapsedSize={3}
          onCollapse={() => setIsExplorerCollapsed(true)}
          onExpand={() => setIsExplorerCollapsed(false)}
          className={cn("min-w-[180px]", isExplorerCollapsed && "min-w-[44px]")}
          id="explorer-panel"
        >
          {isExplorerCollapsed ? (
            <button
              type="button"
              className={cn(
                "h-full w-full flex flex-col items-center justify-start",
                "bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700",
                "hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              )}
              onClick={() => explorerPanelRef.current?.expand(12)}
              title="Expand Explorer"
            >
              <div className="pt-3 text-gray-700 dark:text-gray-200">
                <ChevronRight className="h-5 w-5" />
              </div>
              <div className="mt-3 text-xs font-semibold text-gray-700 dark:text-gray-200 [writing-mode:vertical-rl] rotate-180 tracking-wide">
                Explorer
              </div>
            </button>
          ) : (
            <ExplorerPanel onCollapse={() => explorerPanelRef.current?.collapse()} />
          )}
        </Panel>

        {/* Resize Handle: Explorer ↔ Main */}
        <PanelResizeHandle className="w-1 bg-gray-200 hover:bg-blue-500 transition-colors cursor-col-resize" />

        {/* Middle Column: Session Tabs + Editor + Terminal */}
        <Panel
          defaultSize={66}
          minSize={30}
          className="min-w-[300px]"
          id="main-column"
        >
          <div className="flex flex-col h-full">
            {/* Session Tab Bar */}
            <SessionTabBar
              sessions={orderedSessions}
              currentSessionId={currentSessionId}
              onSessionSelect={handleSessionSelect}
              onSessionCreate={handleSessionCreate}
              onSessionRename={handleSessionRename}
              onSessionDelete={handleSessionDelete}
              onSessionReorder={handleSessionReorder}
              collapsed={isSessionBarCollapsed}
              onToggleCollapse={() => setIsSessionBarCollapsed(!isSessionBarCollapsed)}
            />

            {/* Editor + Terminal (vertical split) */}
            <div className="flex-1 overflow-hidden">
              <PanelGroup
                direction="vertical"
                className="h-full"
                autoSaveId="workbench-main-column:v1"
              >
                {/* Top: Editor/Artifacts */}
                <Panel
                  defaultSize={isTerminalOpen ? 100 - terminalSize : 100}
                  minSize={30}
                  className="min-h-[200px]"
                  id="editor-panel"
                >
                  <ArtifactsPanel />
                </Panel>

                {/* Bottom: Terminal/Console (collapsible) */}
                {isTerminalOpen && (
                  <>
                    <PanelResizeHandle className="h-1 bg-gray-700 hover:bg-blue-500 transition-colors cursor-row-resize" />
                    <Panel
                      defaultSize={terminalSize}
                      minSize={15}
                      maxSize={60}
                      className="min-h-[100px]"
                      id="terminal-panel"
                      onResize={(size) => setTerminalSize(size)}
                    >
                      <ConsolePanel onToggleCollapse={toggleTerminal} isCollapsed={false} />
                    </Panel>
                  </>
                )}

                {/* Collapsed state: minimal bar to re-open */}
                {!isTerminalOpen && (
                  <div
                    className={cn(
                      "flex items-center justify-center px-3 py-1",
                      "bg-gray-800 text-gray-400 cursor-pointer",
                      "hover:bg-gray-700 hover:text-gray-200 transition-colors"
                    )}
                    onClick={toggleTerminal}
                  >
                    <ChevronUp className="h-4 w-4 mr-1" />
                    <span className="text-xs">Show Console</span>
                  </div>
                )}
              </PanelGroup>
            </div>
          </div>
        </Panel>

        {/* Resize Handle: Main ↔ Chat */}
        <PanelResizeHandle className="w-1 bg-gray-200 hover:bg-blue-500 transition-colors cursor-col-resize" />

        {/* Right Panel: Chat (collapsible) */}
        <Panel
          ref={chatPanelRef}
          defaultSize={22}
          minSize={18}
          maxSize={45}
          collapsible
          collapsedSize={3}
          onCollapse={() => setIsChatCollapsed(true)}
          onExpand={() => setIsChatCollapsed(false)}
          className={cn("min-w-[280px]", isChatCollapsed && "min-w-[44px]")}
          id="chat-panel"
        >
          {isChatCollapsed ? (
            <button
              type="button"
              className={cn(
                "h-full w-full flex flex-col items-center justify-start",
                "bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700",
                "hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              )}
              onClick={() => chatPanelRef.current?.expand(22)}
              title="Expand Chat"
            >
              <div className="pt-3 text-gray-700 dark:text-gray-200">
                <ChevronLeft className="h-5 w-5" />
              </div>
              <div className="mt-3 text-xs font-semibold text-gray-700 dark:text-gray-200 [writing-mode:vertical-rl] rotate-180 tracking-wide">
                Chat
              </div>
            </button>
          ) : (
            <ReasoningPanel onCollapse={() => chatPanelRef.current?.collapse()} />
          )}
        </Panel>
      </PanelGroup>
    </div>
  );
}
