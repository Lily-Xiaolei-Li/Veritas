/**
 * Auth Store (B1.6 - Authentication & API Key UI)
 *
 * Zustand store for managing authentication state.
 * Uses persist middleware to store token in localStorage.
 *
 * SECURITY NOTES:
 * - Only token and tokenExpiresAt are persisted (minimal data)
 * - User object is kept in memory only (reconstructed on load)
 * - tokenExpiresAt is informational only - 401 is authoritative
 * - localStorage is vulnerable to XSS - mitigated by short token lifetime
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { AUTH_STORAGE_KEY } from "@/lib/utils/constants";
import type { AuthUser, AuthStatus } from "@/lib/api/types";

// =============================================================================
// Types
// =============================================================================

interface AuthState {
  // Persisted state (minimal - in localStorage)
  token: string | null;
  tokenExpiresAt: number | null;

  // Memory-only state (not persisted)
  authStatus: AuthStatus;
  user: AuthUser | null;
  sessionExpiredShown: boolean;

  // Derived getter
  isAuthenticated: () => boolean;

  // Actions
  setAuthStatus: (status: AuthStatus) => void;
  login: (token: string, user: AuthUser, expiresInHours: number) => void;
  logout: () => void;
  setSessionExpiredShown: (shown: boolean) => void;
  clearSessionExpired: () => void;

  // Internal action for restoring user from token on app load
  setUser: (user: AuthUser | null) => void;
}

// =============================================================================
// Store Implementation
// =============================================================================

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      token: null,
      tokenExpiresAt: null,
      authStatus: "checking",
      user: null,
      sessionExpiredShown: false,

      // Derived getter
      isAuthenticated: () => get().token !== null,

      // Actions
      setAuthStatus: (status) => set({ authStatus: status }),

      login: (token, user, expiresInHours) => {
        const expiresAt = Date.now() + expiresInHours * 60 * 60 * 1000;
        set({
          token,
          tokenExpiresAt: expiresAt,
          user,
          authStatus: "enabled",
          sessionExpiredShown: false,
        });
      },

      logout: () => {
        set({
          token: null,
          tokenExpiresAt: null,
          user: null,
          sessionExpiredShown: false,
        });
      },

      setSessionExpiredShown: (shown) => set({ sessionExpiredShown: shown }),

      clearSessionExpired: () => set({ sessionExpiredShown: false }),

      setUser: (user) => set({ user }),
    }),
    {
      name: AUTH_STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      // Only persist token and expiry - minimal data for security
      partialize: (state) => ({
        token: state.token,
        tokenExpiresAt: state.tokenExpiresAt,
      }),
    }
  )
);

// =============================================================================
// Selectors (for cleaner component usage)
// =============================================================================

export const selectToken = (state: AuthState) => state.token;
export const selectAuthStatus = (state: AuthState) => state.authStatus;
export const selectUser = (state: AuthState) => state.user;
export const selectIsAuthenticated = (state: AuthState) => state.isAuthenticated();
export const selectSessionExpiredShown = (state: AuthState) => state.sessionExpiredShown;
