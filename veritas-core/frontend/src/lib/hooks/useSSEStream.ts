/**
 * SSE Stream Hook (B1.4 - Kill Switch)
 * B1.6 - Updated to support auth token via query string
 *
 * React hook for managing SSE connection lifecycle.
 * Automatically connects when sessionId is set and cleans up on unmount.
 * Handles artifact_created events for real-time updates.
 * Handles run_terminated events from kill switch (B1.4).
 *
 * Note: EventSource API cannot set custom headers, so auth token is passed
 * via query string when authenticated. This is a known tradeoff for local-first
 * deployment.
 */

import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { SSEClient } from "@/lib/stream/SSEClient";
import { useWorkbenchStore } from "@/lib/store";
import { API_BASE_URL } from "@/lib/utils/constants";
import { getAuthenticatedSSEUrl } from "@/lib/api/authFetch";

interface UseSSEStreamOptions {
  /** Whether to automatically connect when sessionId is available */
  autoConnect?: boolean;
}

interface UseSSEStreamReturn {
  /** Manually trigger connection (if autoConnect is false) */
  connect: () => void;
  /** Manually disconnect */
  disconnect: () => void;
  /** Whether the SSE connection is active */
  isConnected: boolean;
  /** Current error message, if any */
  error: string | null;
}

/**
 * Hook for managing SSE stream connection to a session.
 *
 * @param sessionId - The session ID to connect to (null to disconnect)
 * @param options - Configuration options
 * @returns Connection state and control methods
 */
export function useSSEStream(
  sessionId: string | null,
  options: UseSSEStreamOptions = {}
): UseSSEStreamReturn {
  const { autoConnect = true } = options;

  const clientRef = useRef<SSEClient | null>(null);
  const queryClient = useQueryClient();

  // Get store actions
  const {
    appendToStreamingMessage,
    finalizeStreamingMessage,
    addToolEvent,
    updateToolEvent,
    clearToolEvents,
    setSSEConnected,
    setSSEError,
    sseConnected,
    sseError,
    // B1.4 - Kill switch
    markTerminated,
    clearExecutionState,
    // B2.2 - Brain events
    addBrainEvent,
    clearBrainEvents,
  } = useWorkbenchStore();

  /**
   * Connect to SSE stream for the current session.
   */
  const connect = useCallback(() => {
    if (!sessionId) {
      console.warn("useSSEStream: Cannot connect without sessionId");
      return;
    }

    // Cleanup existing connection
    if (clientRef.current) {
      clientRef.current.cleanup();
    }

    // Clear events from previous run
    clearToolEvents();
    clearBrainEvents();

    // Build SSE URL with auth token if authenticated
    const baseUrl = `${API_BASE_URL}/api/v1/sessions/${sessionId}/stream`;
    const url = getAuthenticatedSSEUrl(baseUrl);

    clientRef.current = new SSEClient(url, {
      onToken: (data) => {
        appendToStreamingMessage(data.run_id, data.content);
      },

      onToolStart: (data) => {
        addToolEvent({
          tool_call_id: data.tool_call_id,
          tool_name: data.tool_name,
          input_preview: data.input_preview,
          status: "running",
        });
      },

      onToolEnd: (data) => {
        updateToolEvent(data.tool_call_id, {
          status: data.exit_code === 0 ? "completed" : "failed",
          exit_code: data.exit_code,
          output_preview: data.output_preview,
          duration_ms: data.duration_ms,
        });
      },

      onError: (data) => {
        setSSEError(data.message);
        // Don't auto-clear error - let UI handle it
      },

      onDone: (data) => {
        finalizeStreamingMessage(data.run_id);
        // Clear execution state on normal completion (B1.4)
        clearExecutionState();
      },

      onConnectionChange: (connected) => {
        setSSEConnected(connected);
        if (connected) {
          setSSEError(null);
        }
      },

      // B1.3 - Handle artifact created events
      onArtifactCreated: (data) => {
        // Invalidate artifact queries to trigger refetch
        queryClient.invalidateQueries({ queryKey: ["session-artifacts", sessionId] });
        queryClient.invalidateQueries({ queryKey: ["run-artifacts", data.artifact.run_id] });
        console.log("SSE: Artifact created", data.artifact.display_name);
      },

      // B1.4 - Handle run terminated events (kill switch)
      onRunTerminated: (data) => {
        console.log("SSE: Run terminated", data.run_id, data.reason);
        markTerminated({
          reason: data.reason,
          message: data.message,
          latency_ms: data.latency_ms,
        });
      },

      // B2.2 - Multi-brain events
      onClassification: (data) => {
        console.log("SSE: Classification", data.complexity, data.mode, data.reason_code);
        addBrainEvent({
          run_id: data.run_id,
          type: "classification",
          data: data,
        });
      },

      onBrainThinking: (data) => {
        console.log("SSE: Brain thinking", data.brain, data.decision.intent);
        addBrainEvent({
          run_id: data.run_id,
          type: "brain_thinking",
          data: data,
        });
      },

      onDeliberationRound: (data) => {
        console.log("SSE: Deliberation round", data.round_display, "/", data.max_rounds);
        addBrainEvent({
          run_id: data.run_id,
          type: "deliberation_round",
          data: data,
        });
      },

      onConsensusReached: (data) => {
        console.log("SSE: Consensus reached", data.intent);
        addBrainEvent({
          run_id: data.run_id,
          type: "consensus_reached",
          data: data,
        });
      },

      onConsensusFailed: (data) => {
        console.log("SSE: Consensus failed", data.reason);
        addBrainEvent({
          run_id: data.run_id,
          type: "consensus_failed",
          data: data,
        });
      },

      onEscalationRequired: (data) => {
        console.log("SSE: Escalation required", data.reason);
        addBrainEvent({
          run_id: data.run_id,
          type: "escalation_required",
          data: data,
        });
      },
    });

    clientRef.current.connect();
  }, [
    sessionId,
    appendToStreamingMessage,
    finalizeStreamingMessage,
    addToolEvent,
    updateToolEvent,
    clearToolEvents,
    setSSEConnected,
    setSSEError,
    markTerminated,
    clearExecutionState,
    queryClient,
    // B2.2
    addBrainEvent,
    clearBrainEvents,
  ]);

  /**
   * Disconnect from SSE stream.
   */
  const disconnect = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.cleanup();
      clientRef.current = null;
    }
    setSSEConnected(false);
  }, [setSSEConnected]);

  // Auto-connect when sessionId changes (if enabled)
  useEffect(() => {
    if (autoConnect && sessionId) {
      connect();
    }

    // Cleanup on unmount or session change
    return () => {
      if (clientRef.current) {
        clientRef.current.cleanup();
        clientRef.current = null;
      }
    };
  }, [sessionId, autoConnect, connect]);

  return {
    connect,
    disconnect,
    isConnected: sseConnected,
    error: sseError,
  };
}
