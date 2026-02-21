/**
 * Application Constants
 *
 * B1.0 - Workbench Shell
 * B1.6 - Authentication & API Key UI
 */

export const APP_NAME = "Agent B Research";
export const APP_VERSION = "1.1.0";

// API Configuration
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// Health Check Configuration
export const HEALTH_CHECK_INTERVAL = 30000; // 30 seconds

// Default Session ID for development
export const DEFAULT_SESSION_ID = "default-session";

// =============================================================================
// LLM Provider Configuration (B1.6)
// =============================================================================

/**
 * Available LLM providers for API key management.
 * Update when B2.0 (LLM Provider Abstraction) adds new providers.
 */
export const LLM_PROVIDERS = [
  "gemini",
  "openai",
  "openrouter",
  "anthropic",
  "ollama",
] as const;

export type LLMProvider = (typeof LLM_PROVIDERS)[number];

/**
 * Human-readable labels for LLM providers.
 */
export const LLM_PROVIDER_LABELS: Record<LLMProvider, string> = {
  gemini: "Google Gemini",
  openai: "OpenAI",
  openrouter: "OpenRouter",
  anthropic: "Anthropic",
  ollama: "Ollama (Local)",
};

// =============================================================================
// Auth Configuration (B1.6)
// =============================================================================

/** Key used for persisting auth state in localStorage */
export const AUTH_STORAGE_KEY = "agent-b-auth";
