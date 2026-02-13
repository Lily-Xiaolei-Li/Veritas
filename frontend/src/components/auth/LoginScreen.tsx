/**
 * Login Screen Component (B1.6 - Authentication & API Key UI)
 *
 * Full-screen login form with:
 * - Username/password inputs
 * - Submit button with loading state
 * - Error display
 * - "Session expired" message when applicable
 */

"use client";

import React, { useState } from "react";
import { Loader2 } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { useLogin, useSessionExpired } from "@/lib/hooks/useAuth";
import { APP_NAME } from "@/lib/utils/constants";
import { cn } from "@/lib/utils/cn";

// =============================================================================
// Component
// =============================================================================

export function LoginScreen() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const { mutate: login, isPending } = useLogin();
  const { sessionExpiredShown, clearSessionExpired } = useSessionExpired();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    // Clear session expired message on new login attempt
    if (sessionExpiredShown) {
      clearSessionExpired();
    }

    // Basic validation
    if (!username.trim()) {
      setFormError("Username is required");
      return;
    }
    if (!password) {
      setFormError("Password is required");
      return;
    }

    login(
      { username: username.trim(), password },
      {
        onError: (error) => {
          setFormError(error.message || "Login failed. Please try again.");
        },
      }
    );
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">{APP_NAME}</h1>
          <p className="mt-2 text-gray-600">
            Sign in to access your cognitive workbench
          </p>
        </div>

        {/* Session expired banner */}
        {sessionExpiredShown && (
          <div
            className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md"
            role="alert"
          >
            <p className="text-sm text-yellow-800">
              Your session has expired. Please sign in again.
            </p>
          </div>
        )}

        {/* Login form */}
        <form
          onSubmit={handleSubmit}
          className="bg-white shadow-md rounded-lg px-8 py-8"
        >
          <div className="space-y-4">
            <Input
              label="Username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              autoComplete="username"
              disabled={isPending}
              autoFocus
            />

            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              autoComplete="current-password"
              disabled={isPending}
            />
          </div>

          {/* Error message */}
          {formError && (
            <div
              className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md"
              role="alert"
            >
              <p className="text-sm text-red-800">{formError}</p>
            </div>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={isPending}
            className={cn(
              "w-full mt-6 py-2.5 px-4 rounded-md font-medium",
              "text-white bg-blue-600 hover:bg-blue-700",
              "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
              "disabled:bg-blue-400 disabled:cursor-not-allowed",
              "transition-colors"
            )}
          >
            {isPending ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Signing in...
              </span>
            ) : (
              "Sign in"
            )}
          </button>
        </form>

        {/* Footer */}
        <p className="mt-4 text-center text-sm text-gray-500">
          Local-first AI assistant
        </p>
      </div>
    </div>
  );
}
