import { describe, it, expect, beforeEach } from "vitest";

import { useWorkbenchStore } from "@/lib/store";

// These are intentionally lightweight “smoke” tests to ensure the frontend
// test runner is wired correctly in CI and that core store actions behave.

describe("Workbench store (smoke)", () => {
  beforeEach(() => {
    const s = useWorkbenchStore.getState();

    // reset the specific state we touch in tests
    s.clearFileSelection();
    s.clearToolEvents();
    s.clearExecutionState();
  });

  it("toggles file selection", () => {
    const s = useWorkbenchStore.getState();

    expect(s.selectedFileIds).toEqual([]);

    s.toggleFileSelection("a.txt");
    expect(useWorkbenchStore.getState().selectedFileIds).toEqual(["a.txt"]);

    s.toggleFileSelection("a.txt");
    expect(useWorkbenchStore.getState().selectedFileIds).toEqual([]);
  });

  it("tracks execution lifecycle (basic)", () => {
    const s = useWorkbenchStore.getState();

    expect(s.executionStatus).toBe("idle");
    expect(s.activeRunId).toBeNull();

    s.setActiveRun("run-1");
    expect(useWorkbenchStore.getState().activeRunId).toBe("run-1");
    expect(useWorkbenchStore.getState().executionStatus).toBe("running");

    s.setTerminating();
    expect(useWorkbenchStore.getState().executionStatus).toBe("terminating");

    s.markCompleted();
    expect(useWorkbenchStore.getState().executionStatus).toBe("completed");

    s.clearExecutionState();
    expect(useWorkbenchStore.getState().executionStatus).toBe("idle");
    expect(useWorkbenchStore.getState().activeRunId).toBeNull();
  });
});
