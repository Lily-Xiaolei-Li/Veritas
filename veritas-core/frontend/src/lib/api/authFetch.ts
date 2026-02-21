/**
 * Authenticated Fetch Wrapper (B1.6 - Authentication & API Key UI)
 *
 * Wraps fetch() to:
 * - Add Authorization: Bearer <token> header when authenticated
 * - Handle 401 responses with dedupe logic
 * - Clear auth state on session expiry
 *
 * DOES NOT handle SSE (EventSource cannot use custom headers).
 * For SSE, pass token via query string - see SSEClient.
 */

import { useAuthStore } from "@/lib/store";

// =============================================================================
// Types
// =============================================================================

interface AuthFetchOptions extends RequestInit {
  /** Skip authentication header (for public endpoints) */
  skipAuth?: boolean;
}

// =============================================================================
// Auth Fetch Implementation
// =============================================================================

/**
 * Fetch wrapper that adds auth header and handles 401 responses.
 *
 * @param url - The URL to fetch
 * @param options - Fetch options (extends RequestInit)
 * @returns Promise<Response>
 *
 * @example
 * const response = await authFetch('/api/v1/sessions');
 * const data = await response.json();
 *
 * @example
 * // Skip auth for specific request
 * const response = await authFetch('/api/v1/health', { skipAuth: true });
 */
export async function authFetch(
  url: string,
  options: AuthFetchOptions = {}
): Promise<Response> {
  const { skipAuth = false, headers: customHeaders, ...fetchOptions } = options;

  // Get current auth state
  const token = useAuthStore.getState().token;

  // Build headers
  const headers = new Headers(customHeaders);

  // Add auth header if authenticated and not skipping
  if (token && !skipAuth) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  // Ensure Content-Type for JSON bodies
  if (
    fetchOptions.body &&
    typeof fetchOptions.body === "string" &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  // Make the request
  const response = await fetch(url, {
    ...fetchOptions,
    headers,
  });

  // Handle 401 Unauthorized
  if (response.status === 401) {
    handleUnauthorized();
  }

  return response;
}

/**
 * Handle 401 response with dedupe logic.
 * Only shows session expired message once per session.
 */
function handleUnauthorized(): void {
  const store = useAuthStore.getState();

  // Dedupe: only handle if not already shown
  if (!store.sessionExpiredShown) {
    store.setSessionExpiredShown(true);
    store.logout();
    // The AuthGuard component will redirect to login screen
    // based on authStatus and token state
  }
}

// =============================================================================
// Convenience Functions
// =============================================================================

/**
 * GET request with auth.
 */
export async function authGet(url: string, options?: AuthFetchOptions): Promise<Response> {
  return authFetch(url, { ...options, method: "GET" });
}

/**
 * POST request with auth.
 */
export async function authPost(
  url: string,
  body?: unknown,
  options?: AuthFetchOptions
): Promise<Response> {
  return authFetch(url, {
    ...options,
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * PUT request with auth.
 */
export async function authPut(
  url: string,
  body?: unknown,
  options?: AuthFetchOptions
): Promise<Response> {
  return authFetch(url, {
    ...options,
    method: "PUT",
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * PATCH request with auth.
 */
export async function authPatch(
  url: string,
  body?: unknown,
  options?: AuthFetchOptions
): Promise<Response> {
  return authFetch(url, {
    ...options,
    method: "PATCH",
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * DELETE request with auth.
 */
export async function authDelete(
  url: string,
  options?: AuthFetchOptions
): Promise<Response> {
  return authFetch(url, { ...options, method: "DELETE" });
}

// =============================================================================
// SSE Token Helper
// =============================================================================

/**
 * Get the SSE URL with token query parameter for authenticated streaming.
 *
 * EventSource API cannot set custom headers, so we pass token via query string.
 * This is a known tradeoff for local-first deployment.
 *
 * @param baseUrl - The SSE endpoint URL
 * @returns URL with ?token= appended if authenticated
 */
export function getAuthenticatedSSEUrl(baseUrl: string): string {
  const token = useAuthStore.getState().token;

  if (!token) {
    return baseUrl;
  }

  const url = new URL(baseUrl, window.location.origin);
  url.searchParams.set("token", token);
  return url.toString();
}
