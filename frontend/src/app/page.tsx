/**
 * Agent B - Main Page
 *
 * B1.0 - Workbench Shell
 * B1.4 - Kill Switch
 * B1.5 - Session Management UI
 * B1.6 - Authentication & API Key UI
 */

"use client";

import { useEffect, useState } from "react";
import { LogOut, RotateCcw, Save, Undo2, Download, Upload, FolderOpen, FilePlus2 } from "lucide-react";
import { WorkbenchLayout } from "@/components/workbench/WorkbenchLayout";
import { HealthIndicator } from "@/components/health/HealthIndicator";
import { KillSwitchButton } from "@/components/workbench/KillSwitchButton";
import { SettingsModal, SettingsButton } from "@/components/settings";
import { useLogout } from "@/lib/hooks/useAuth";
import { useAuthStore, useWorkbenchStore } from "@/lib/store";
import { APP_VERSION } from "@/lib/utils/constants";
import { cn } from "@/lib/utils/cn";
import { exportWorkspace, getUndoStack, importWorkspace, saveWorkspace, undoLatest, resetWorkspace } from "@/lib/api/workspace";

export default function Home() {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isWorkspaceMenuOpen, setIsWorkspaceMenuOpen] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [undoCount, setUndoCount] = useState<number>(0);
  const [showNewProjectConfirm, setShowNewProjectConfirm] = useState(false);
  const { authStatus, user, isAuthenticated } = useAuthStore();
  const currentSessionId = useWorkbenchStore((s) => s.currentSessionId);
  const logout = useLogout();

  const refreshUndo = async () => {
    if (!currentSessionId) {
      setUndoCount(0);
      return;
    }
    try {
      const stack = await getUndoStack(currentSessionId);
      setUndoCount(stack.items?.length || 0);
    } catch {
      // ignore
      setUndoCount(0);
    }
  };

  const doSave = async () => {
    if (!currentSessionId) {
      alert("No active session to save.");
      return;
    }

    try {
      const resp = await saveWorkspace(currentSessionId);
      const t = new Date(resp.saved_at);
      setSaveStatus(`Saved ✓ ${t.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`);
      // Clear after a bit
      window.setTimeout(() => setSaveStatus(null), 3000);
    } catch (e) {
      alert(`Save failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const doUndo = async () => {
    if (!currentSessionId) {
      alert("No active session.");
      return;
    }

    try {
      const resp = await undoLatest(currentSessionId);
      if (!resp.ok) {
        alert("Nothing to undo.");
      }
      await refreshUndo();
    } catch (e) {
      alert(`Undo failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const doExport = async () => {
    if (!currentSessionId) {
      alert("No active session.");
      return;
    }
    try {
      const blob = await exportWorkspace(currentSessionId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `workspace_${currentSessionId.slice(0, 8)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`Export failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  const doImport = async () => {
    // file picker
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json,application/json";
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;

      const text = await file.text();
      let data: unknown;
      try {
        data = JSON.parse(text);
      } catch {
        alert("Invalid JSON file.");
        return;
      }

      const mode = (confirm("Import mode: OK = MERGE (safe) / Cancel = REPLACE (dangerous). Continue?") ? "merge" : "replace") as
        | "merge"
        | "replace";

      if (mode === "replace") {
        const ok = confirm("REPLACE will wipe ALL existing sessions/messages/artifacts in the DB. Are you absolutely sure?");
        if (!ok) return;
      }

      try {
        await importWorkspace(data, mode);
        // simplest: reload
        window.location.reload();
      } catch (e) {
        alert(`Import failed: ${e instanceof Error ? e.message : String(e)}`);
      }
    };
    input.click();
  };

  const doNewProject = async () => {
    try {
      await resetWorkspace();
      // Reload to reset all frontend state
      window.location.reload();
    } catch (e) {
      alert(`Reset failed: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  // Stage 14: Focused artifacts (pinned context)
  // Session-level focus controls live in the Artifacts toolbar now.

  useEffect(() => {
    void refreshUndo();
  }, [currentSessionId]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const key = e.key.toLowerCase();
      const isMod = e.metaKey || e.ctrlKey;

      if (isMod && key === "s") {
        e.preventDefault();
        void doSave();
      }

      if (isMod && key === "z") {
        e.preventDefault();
        void doUndo();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [currentSessionId, undoCount]);

  const resetLayout = () => {
    const ok = confirm(
      "Reset layout to defaults? This will clear saved panel sizes and reload the page."
    );
    if (!ok) return;

    const keys = [
      "react-resizable-panels:workbench-layout:v1",
      "react-resizable-panels:workbench-main-column:v1",
      "react-resizable-panels:artifact-browser:v1",
    ];

    for (const k of keys) {
      try {
        localStorage.removeItem(k);
      } catch {
        // ignore
      }
    }

    window.location.reload();
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-950">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-2 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
        <div className="flex items-center gap-4">
          <h1 className="text-xl text-gray-900 dark:text-gray-100">
            <span className="font-bold">Agent B</span>
            {" "}
            <span className="italic text-blue-500 font-normal">Research</span>
          </h1>
          <span className="text-sm text-gray-500 dark:text-gray-400">v{APP_VERSION}</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Kill Switch - always visible when execution is active */}
          <KillSwitchButton />

          {/* Divider */}
          <div className="w-px h-6 bg-gray-200 dark:bg-gray-700 mx-1" />

          {/* Workspace Controls: Collapsible menu */}
          <div className="relative">
            <button
              onClick={() => {
                const next = !isWorkspaceMenuOpen;
                setIsWorkspaceMenuOpen(next);
                if (next) void refreshUndo();
              }}
              className={cn(
                "p-2 rounded-md transition-colors",
                "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200",
                "hover:bg-gray-100 dark:hover:bg-gray-800",
                "focus:outline-none focus:ring-2 focus:ring-blue-500",
                isWorkspaceMenuOpen && "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200"
              )}
              title="File menu (Save, Undo, Export, Import)"
              aria-label="File menu"
            >
              <FolderOpen className="h-5 w-5" />
            </button>

            {/* Dropdown menu */}
            {isWorkspaceMenuOpen && (
              <>
                {/* Backdrop to close menu */}
                <div 
                  className="fixed inset-0 z-10" 
                  onClick={() => setIsWorkspaceMenuOpen(false)} 
                />
                <div className="absolute top-full right-0 mt-1 z-20 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg py-1 min-w-[140px]">
                  <button
                    onClick={async () => { await doSave(); setIsWorkspaceMenuOpen(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <Save className="h-4 w-4" />
                    <span>Save</span>
                    <span className="ml-auto text-xs text-gray-400">⌘S</span>
                  </button>
                  {saveStatus && (
                    <div className="px-3 pb-2 text-[11px] text-green-600 dark:text-green-400">
                      {saveStatus}
                    </div>
                  )}
                  <button
                    onClick={async () => { await doUndo(); setIsWorkspaceMenuOpen(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <Undo2 className="h-4 w-4" />
                    <span>Undo</span>
                    {undoCount > 0 ? (
                      <span className="ml-auto text-xs text-gray-500 dark:text-gray-300">{undoCount}</span>
                    ) : (
                      <span className="ml-auto text-xs text-gray-400">⌘Z</span>
                    )}
                  </button>
                  <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
                  <button
                    onClick={async () => { await doExport(); setIsWorkspaceMenuOpen(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <Download className="h-4 w-4" />
                    Export
                  </button>
                  <button
                    onClick={async () => { await doImport(); setIsWorkspaceMenuOpen(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    <Upload className="h-4 w-4" />
                    Import
                  </button>
                  <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
                  <button
                    onClick={() => { setShowNewProjectConfirm(true); setIsWorkspaceMenuOpen(false); }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30"
                  >
                    <FilePlus2 className="h-4 w-4" />
                    New Project
                  </button>
                </div>
              </>
            )}
          </div>

          {/* Divider */}
          <div className="w-px h-6 bg-gray-200 dark:bg-gray-700 mx-1" />

          <HealthIndicator />

          {/* Divider */}
          <div className="w-px h-6 bg-gray-200 dark:bg-gray-700 mx-2" />

          {/* Reset layout */}
          <button
            onClick={resetLayout}
            className={cn(
              "p-2 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-100",
              "hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors",
              "focus:outline-none focus:ring-2 focus:ring-blue-500"
            )}
            title="Reset layout"
            aria-label="Reset layout"
          >
            <RotateCcw className="h-5 w-5" />
          </button>

          {/* Settings button */}
          <SettingsButton onClick={() => setIsSettingsOpen(true)} />

          {/* User info and logout (only when auth enabled and authenticated) */}
          {authStatus === "enabled" && isAuthenticated() && (
            <>
              {user && (
                <span className="text-sm text-gray-600 dark:text-gray-300 px-2">
                  {user.username}
                </span>
              )}
              <button
                onClick={logout}
                className={cn(
                  "p-2 text-gray-500 hover:text-gray-700 dark:text-gray-300 dark:hover:text-gray-100",
                  "hover:bg-gray-100 dark:hover:bg-gray-800 rounded-md transition-colors",
                  "focus:outline-none focus:ring-2 focus:ring-blue-500"
                )}
                aria-label="Sign out"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </>
          )}
        </div>
      </header>

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Workbench */}
        <main className="flex-1 overflow-hidden">
          <WorkbenchLayout />
        </main>
      </div>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />

      {/* New Project Confirmation Dialog */}
      {showNewProjectConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div 
            className="absolute inset-0 bg-black/50" 
            onClick={() => setShowNewProjectConfirm(false)} 
          />
          {/* Dialog */}
          <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md mx-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
              Start New Project?
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              This will <span className="font-semibold text-red-600 dark:text-red-400">permanently delete</span> all sessions, messages, and artifacts in the current workspace.
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">
              This action cannot be undone. Make sure you have exported any important work.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowNewProjectConfirm(false)}
                className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  setShowNewProjectConfirm(false);
                  await doNewProject();
                }}
                className="px-4 py-2 text-sm bg-red-600 text-white hover:bg-red-700 rounded-md transition-colors"
              >
                Delete Everything & Start Fresh
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
