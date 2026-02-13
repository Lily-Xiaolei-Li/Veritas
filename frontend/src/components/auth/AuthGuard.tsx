/**
 * Auth Guard Component (B1.6 - Authentication & API Key UI)
 *
 * Handles all 5 authentication states:
 * - checking: Spinner "Connecting..."
 * - offline: "Cannot connect to backend" with retry button
 * - disabled: Render workbench (children)
 * - enabled + not authenticated: Login screen
 * - enabled + authenticated: Render workbench (children)
 */

"use client";

import React from "react";
import { Loader2, WifiOff } from "lucide-react";
import { LoginScreen } from "./LoginScreen";
import { useAuthStatus } from "@/lib/hooks/useAuth";
import { cn } from "@/lib/utils/cn";
import { API_BASE_URL } from "@/lib/utils/constants";

// =============================================================================
// Types
// =============================================================================

interface AuthGuardProps {
  children: React.ReactNode;
}

// =============================================================================
// Sub-components
// =============================================================================

function CheckingState() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50">
      <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      <p className="mt-4 text-gray-600">Connecting...</p>
    </div>
  );
}

function OfflineState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
      <div className="text-center">
        <WifiOff className="h-12 w-12 text-red-500 mx-auto" />
        <h2 className="mt-4 text-xl font-semibold text-gray-900">
          Cannot connect to backend
        </h2>
        <p className="mt-2 text-gray-600 max-w-sm">
          Please make sure the backend server is running and reachable at: {API_BASE_URL}
        </p>
        <button
          onClick={onRetry}
          className={cn(
            "mt-6 px-4 py-2 rounded-md font-medium",
            "text-white bg-blue-600 hover:bg-blue-700",
            "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
            "transition-colors"
          )}
        >
          Retry connection
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// Auth Indicator
// =============================================================================

// NOTE: We intentionally do NOT show a floating "Auth not available" badge.
// It now lives in the Terminal → Status tab to avoid blocking UI controls.

// =============================================================================
// Main Component
// =============================================================================

export function AuthGuard({ children }: AuthGuardProps) {
  const { authStatus, isAuthenticated, retry } = useAuthStatus();

  // State: Checking connection
  if (authStatus === "checking") {
    return <CheckingState />;
  }

  // State: Backend offline
  if (authStatus === "offline") {
    return <OfflineState onRetry={retry} />;
  }

  // State: Auth disabled - render workbench
  if (authStatus === "disabled") {
    return <>{children}</>;
  }

  // State: Auth enabled but not authenticated - show login
  if (authStatus === "enabled" && !isAuthenticated) {
    return <LoginScreen />;
  }

  // State: Auth enabled and authenticated - render workbench
  return <>{children}</>;
}
