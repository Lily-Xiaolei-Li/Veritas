/**
 * Auth Hooks (B1.6 - Authentication & API Key UI)
 *
 * React hooks for authentication:
 * - useAuthStatus: Probes backend to determine auth status
 * - useLogin: Mutation for login
 * - useLogout: Clears auth state and query cache
 *
 * Auth Detection Strategy (Hardened):
 * 1. Call /health first - if fails, show "Backend Offline"
 * 2. Probe POST /api/v1/auth/login with dummy credentials:
 *    - 404 with "Authentication not enabled" → Auth disabled → show workbench
 *    - 401 (invalid credentials) → Auth enabled → show login screen
 *    - 422 (validation error but no "not enabled") → Auth enabled → show login
 *    - Network error → should not happen (step 1 passed) → show offline
 */

import { useEffect, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/lib/utils/constants";
import { useAuthStore } from "@/lib/store";
import type { LoginRequest, LoginResponse, AuthStatus } from "@/lib/api/types";

// =============================================================================
// Auth Status Detection
// =============================================================================

/**
 * Hook to detect and manage auth status.
 *
 * Runs on mount to determine:
 * - Is backend reachable?
 * - Is auth enabled on the backend?
 *
 * Also restores user from token if token exists.
 */
export function useAuthStatus() {
  const { authStatus, setAuthStatus, token, setUser, isAuthenticated } = useAuthStore();

  const detectAuthStatus = useCallback(async (): Promise<AuthStatus> => {
    // Use a portable timeout helper (AbortSignal.timeout is not supported in all browsers).
    const fetchWithTimeout = async (url: string, init: RequestInit, timeoutMs: number) => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        return await fetch(url, { ...init, signal: controller.signal });
      } finally {
        clearTimeout(timer);
      }
    };

    try {
      // Step 1: Check if backend is reachable via health endpoint
      const healthResponse = await fetchWithTimeout(
        `${API_BASE_URL}/health`,
        { method: "GET" },
        5000
      );

      if (!healthResponse.ok) {
        return "offline";
      }

      // Step 2: Probe auth endpoint with dummy credentials
      // This triggers the actual auth check inside the login handler
      const authProbeResponse = await fetchWithTimeout(
        `${API_BASE_URL}/api/v1/auth/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: "__probe__", password: "__probe__" }),
        },
        5000
      );

      // Check response body for "Authentication not enabled" message
      if (authProbeResponse.status === 404) {
        try {
          const data = await authProbeResponse.json();
          if (data.detail === "Authentication not enabled") {
            return "disabled";
          }
        } catch {
          // If we can't parse JSON, still treat 404 as disabled
        }
        return "disabled";
      }

      // 401 means auth is enabled but credentials are wrong (expected)
      // 422 at this point shouldn't happen (we sent valid structure)
      // Any other status means auth is enabled
      return "enabled";
    } catch (error) {
      // Network error or timeout
      console.error("Auth status detection failed:", error);
      return "offline";
    }
  }, []);

  // Detect auth status on mount
  useEffect(() => {
    let cancelled = false;

    async function detect() {
      setAuthStatus("checking");
      const status = await detectAuthStatus();

      if (!cancelled) {
        setAuthStatus(status);

        // If auth is enabled and we have a token, try to restore user info
        // In a real app, we'd validate the token with the backend
        // For now, we just check if token exists
        if (status === "enabled" && token) {
          // Token exists - user should be set from login response
          // If user is null, it means we're restoring from localStorage
          // We'll let the backend validate on first API call
        }
      }
    }

    detect();

    return () => {
      cancelled = true;
    };
  }, [detectAuthStatus, setAuthStatus, token, setUser]);

  // Retry detection
  const retry = useCallback(async () => {
    setAuthStatus("checking");
    const status = await detectAuthStatus();
    setAuthStatus(status);
  }, [detectAuthStatus, setAuthStatus]);

  return {
    authStatus,
    isAuthenticated: isAuthenticated(),
    retry,
  };
}

// =============================================================================
// Login Hook
// =============================================================================

async function loginApi(credentials: LoginRequest): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Invalid username or password");
    }
    if (response.status === 422) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || "Validation error");
    }
    throw new Error(`Login failed: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Hook for login mutation.
 */
export function useLogin() {
  const { login } = useAuthStore();

  return useMutation({
    mutationFn: loginApi,
    onSuccess: (data) => {
      login(
        data.token,
        { user_id: data.user_id, username: data.username },
        data.expires_in_hours
      );
    },
  });
}

// =============================================================================
// Logout Hook
// =============================================================================

/**
 * Hook for logout action.
 * Clears auth state and React Query cache.
 */
export function useLogout() {
  const { logout } = useAuthStore();
  const queryClient = useQueryClient();

  return useCallback(() => {
    // Clear auth state
    logout();

    // Clear all cached queries (they may contain user-specific data)
    queryClient.clear();
  }, [logout, queryClient]);
}

// =============================================================================
// Session Expired Hook
// =============================================================================

/**
 * Hook to get session expired state for UI messaging.
 */
export function useSessionExpired() {
  const { sessionExpiredShown, clearSessionExpired } = useAuthStore();

  return {
    sessionExpiredShown,
    clearSessionExpired,
  };
}
