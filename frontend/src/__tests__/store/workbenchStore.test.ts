/**
 * Workbench Store Tests (B1.1 - Streaming Reasoning & Events)
 *
 * Tests for Zustand store reducer/action behavior.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { useWorkbenchStore } from "@/lib/store";

describe("Workbench Store", () => {
  // Reset store before each test
  beforeEach(() => {
    useWorkbenchStore.setState({
      currentSessionId: null,
      messages: [],
      streamingMessage: null,
      toolEvents: [],
      sseConnected: false,
      sseError: null,
    });
  });

  describe("setCurrentSession", () => {
    it("sets the current session ID", () => {
      const { setCurrentSession } = useWorkbenchStore.getState();

      setCurrentSession("session-123");

      const state = useWorkbenchStore.getState();
      expect(state.currentSessionId).toBe("session-123");
    });

    it("clears messages and events when session changes", () => {
      // Set up initial state
      useWorkbenchStore.setState({
        currentSessionId: "old-session",
        messages: [
          {
            id: "msg-1",
            session_id: "old-session",
            role: "user",
            content: "Hello",
            created_at: new Date().toISOString(),
          },
        ],
        toolEvents: [
          {
            tool_call_id: "tc-1",
            tool_name: "test",
            input_preview: "test",
            status: "running",
            timestamp: Date.now(),
          },
        ],
      });

      const { setCurrentSession } = useWorkbenchStore.getState();
      setCurrentSession("new-session");

      const state = useWorkbenchStore.getState();
      expect(state.currentSessionId).toBe("new-session");
      expect(state.messages).toHaveLength(0);
      expect(state.toolEvents).toHaveLength(0);
    });
  });

  describe("appendToStreamingMessage", () => {
    it("creates new streaming message for new run_id", () => {
      const { appendToStreamingMessage } = useWorkbenchStore.getState();

      appendToStreamingMessage("run-1", "Hello");

      const state = useWorkbenchStore.getState();
      expect(state.streamingMessage).toEqual({
        run_id: "run-1",
        content: "Hello",
        isStreaming: true,
      });
    });

    it("appends to existing message for same run_id", () => {
      const { appendToStreamingMessage } = useWorkbenchStore.getState();

      appendToStreamingMessage("run-1", "Hello");
      appendToStreamingMessage("run-1", " World");

      const state = useWorkbenchStore.getState();
      expect(state.streamingMessage?.content).toBe("Hello World");
    });

    it("replaces message when run_id changes (reconnection case)", () => {
      const { appendToStreamingMessage } = useWorkbenchStore.getState();

      appendToStreamingMessage("run-1", "Old content");
      appendToStreamingMessage("run-2", "New content");

      const state = useWorkbenchStore.getState();
      expect(state.streamingMessage?.run_id).toBe("run-2");
      expect(state.streamingMessage?.content).toBe("New content");
    });
  });

  describe("finalizeStreamingMessage", () => {
    it("moves streaming content to messages array", () => {
      useWorkbenchStore.setState({
        currentSessionId: "session-1",
        streamingMessage: {
          run_id: "run-1",
          content: "Streaming content",
          isStreaming: true,
        },
      });

      const { finalizeStreamingMessage } = useWorkbenchStore.getState();
      finalizeStreamingMessage("run-1");

      const state = useWorkbenchStore.getState();
      expect(state.streamingMessage).toBeNull();
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0].content).toBe("Streaming content");
      expect(state.messages[0].role).toBe("assistant");
    });

    it("does nothing if run_id does not match", () => {
      useWorkbenchStore.setState({
        streamingMessage: {
          run_id: "run-1",
          content: "Content",
          isStreaming: true,
        },
      });

      const { finalizeStreamingMessage } = useWorkbenchStore.getState();
      finalizeStreamingMessage("run-2"); // Different run_id

      const state = useWorkbenchStore.getState();
      expect(state.streamingMessage).not.toBeNull();
      expect(state.messages).toHaveLength(0);
    });
  });

  describe("addToolEvent", () => {
    it("adds tool event with timestamp", () => {
      const { addToolEvent } = useWorkbenchStore.getState();

      const before = Date.now();
      addToolEvent({
        tool_call_id: "tc-1",
        tool_name: "bash",
        input_preview: "ls -la",
        status: "running",
      });
      const after = Date.now();

      const state = useWorkbenchStore.getState();
      expect(state.toolEvents).toHaveLength(1);
      expect(state.toolEvents[0].tool_call_id).toBe("tc-1");
      expect(state.toolEvents[0].tool_name).toBe("bash");
      expect(state.toolEvents[0].status).toBe("running");
      expect(state.toolEvents[0].timestamp).toBeGreaterThanOrEqual(before);
      expect(state.toolEvents[0].timestamp).toBeLessThanOrEqual(after);
    });
  });

  describe("updateToolEvent", () => {
    it("updates existing tool event by tool_call_id", () => {
      useWorkbenchStore.setState({
        toolEvents: [
          {
            tool_call_id: "tc-1",
            tool_name: "bash",
            input_preview: "ls -la",
            status: "running",
            timestamp: Date.now(),
          },
        ],
      });

      const { updateToolEvent } = useWorkbenchStore.getState();
      updateToolEvent("tc-1", {
        status: "completed",
        exit_code: 0,
        output_preview: "file1.txt\nfile2.txt",
        duration_ms: 150,
      });

      const state = useWorkbenchStore.getState();
      expect(state.toolEvents[0].status).toBe("completed");
      expect(state.toolEvents[0].exit_code).toBe(0);
      expect(state.toolEvents[0].duration_ms).toBe(150);
    });

    it("does nothing for unknown tool_call_id", () => {
      useWorkbenchStore.setState({
        toolEvents: [
          {
            tool_call_id: "tc-1",
            tool_name: "bash",
            input_preview: "ls -la",
            status: "running",
            timestamp: Date.now(),
          },
        ],
      });

      const { updateToolEvent } = useWorkbenchStore.getState();
      updateToolEvent("tc-unknown", { status: "completed" });

      const state = useWorkbenchStore.getState();
      expect(state.toolEvents[0].status).toBe("running");
    });
  });

  describe("clearToolEvents", () => {
    it("removes all tool events", () => {
      useWorkbenchStore.setState({
        toolEvents: [
          {
            tool_call_id: "tc-1",
            tool_name: "bash",
            input_preview: "test",
            status: "running",
            timestamp: Date.now(),
          },
          {
            tool_call_id: "tc-2",
            tool_name: "python",
            input_preview: "test",
            status: "completed",
            timestamp: Date.now(),
          },
        ],
      });

      const { clearToolEvents } = useWorkbenchStore.getState();
      clearToolEvents();

      const state = useWorkbenchStore.getState();
      expect(state.toolEvents).toHaveLength(0);
    });
  });

  describe("setSSEConnected", () => {
    it("sets connected state", () => {
      const { setSSEConnected } = useWorkbenchStore.getState();

      setSSEConnected(true);
      expect(useWorkbenchStore.getState().sseConnected).toBe(true);

      setSSEConnected(false);
      expect(useWorkbenchStore.getState().sseConnected).toBe(false);
    });

    it("clears error when connected", () => {
      useWorkbenchStore.setState({ sseError: "Previous error" });

      const { setSSEConnected } = useWorkbenchStore.getState();
      setSSEConnected(true);

      const state = useWorkbenchStore.getState();
      expect(state.sseConnected).toBe(true);
      expect(state.sseError).toBeNull();
    });
  });

  describe("setSSEError", () => {
    it("sets error message", () => {
      const { setSSEError } = useWorkbenchStore.getState();

      setSSEError("Connection failed");

      const state = useWorkbenchStore.getState();
      expect(state.sseError).toBe("Connection failed");
    });

    it("can clear error with null", () => {
      useWorkbenchStore.setState({ sseError: "Previous error" });

      const { setSSEError } = useWorkbenchStore.getState();
      setSSEError(null);

      const state = useWorkbenchStore.getState();
      expect(state.sseError).toBeNull();
    });
  });
});
