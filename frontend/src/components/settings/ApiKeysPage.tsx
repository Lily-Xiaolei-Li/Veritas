/**
 * API Keys Page Component
 *
 * Phase 2: Simplified provider configuration.
 *
 * The previous encrypted per-key management was overkill and fragile.
 * We now store provider config directly in the backend (plaintext, per user request).
 *
 * Current UI: OpenRouter config (apiKey + models JSON).
 * Hidden when authStatus === 'disabled'
 */

"use client";

import React, { useMemo, useState } from "react";
import { AlertCircle, Check, Eye, EyeOff, Loader2, Save } from "lucide-react";
import { useTranslations } from "next-intl";
import { Input } from "@/components/ui/Input";
import { cn } from "@/lib/utils/cn";
import { useAuthStore } from "@/lib/store";
import { useLLMProviderConfig, useUpsertLLMProviderConfig } from "@/lib/hooks/useLLMProviderConfig";

const DEFAULT_OPENROUTER_MODELS_EXAMPLE = {
  providers: {
    openrouter: {
      baseUrl: "https://openrouter.ai/api/v1",
      apiKey: "",
      auth: "api-key",
      api: "openai-responses",
      models: [
        {
          id: "deepseek/deepseek-chat-v3-0324",
          name: "DeepSeek Chat V3 0324",
          reasoning: false,
          input: ["text"],
          cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
          contextWindow: 200000,
          maxTokens: 8192,
        },
      ],
    },
  },
};

export function ApiKeysPage() {
  const t = useTranslations("apiKeys");
  const authStatus = useAuthStore((s) => s.authStatus);

  const provider = "openrouter";
  const { data, isLoading, isError, error } = useLLMProviderConfig(provider);
  const upsert = useUpsertLLMProviderConfig(provider);

  const initialConfig = useMemo(() => {
    const cfg = data?.config || { provider };
    return {
      baseUrl: (cfg.baseUrl as string) || "https://openrouter.ai/api/v1",
      apiKey: (cfg.apiKey as string) || "",
      // store models array directly (preferred) OR allow user to paste full blob and we extract.
      models: cfg.models ?? DEFAULT_OPENROUTER_MODELS_EXAMPLE.providers.openrouter.models,
      api: (cfg.api as string) || "openai-responses",
      auth: (cfg.auth as string) || "api-key",
      reasoningEffort: cfg.reasoningEffort ?? "",
    };
  }, [data?.config]);

  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [modelsJson, setModelsJson] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [savedOk, setSavedOk] = useState(false);

  // Populate local state once data is loaded
  React.useEffect(() => {
    if (!data?.config) return;
    setBaseUrl(initialConfig.baseUrl);
    setApiKey(initialConfig.apiKey);
    setModelsJson(JSON.stringify({ models: initialConfig.models }, null, 2));
  }, [data?.config, initialConfig.baseUrl, initialConfig.apiKey, initialConfig.models]);

  // Auth disabled means "no login required" (local machine security). We still allow editing provider settings.
  // Only hide settings if backend is truly offline.

  return (
    <div className="p-6 space-y-6">
      <div className="p-4 rounded border border-amber-300/40 bg-amber-50 text-amber-900 dark:bg-amber-900/20 dark:text-amber-200 flex items-start gap-2">
        <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
        <div className="text-sm">
          <div className="font-medium">
            {authStatus === "disabled" ? t("authOff") : t("authOn")}
          </div>
          <div className="text-xs opacity-90">
            {t("plaintextWarning")}
          </div>
        </div>
      </div>

      <div>
        <div className="text-sm font-semibold text-gray-900 dark:text-gray-100">{t("openRouter")}</div>
        <div className="text-xs text-gray-500 dark:text-gray-400">{t("openRouterDesc")}</div>
      </div>

      {isLoading ? (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t("loading")}
        </div>
      ) : isError ? (
        <div className="text-sm text-red-600">{(error as Error)?.message || t("loadFailed")}</div>
      ) : (
        <div className="space-y-4">
          <Input
            label={t("baseUrl")}
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="https://openrouter.ai/api/v1"
          />

          <div className="relative">
            <Input
              label={t("apiKey")}
              type={showKey ? "text" : "password"}
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-or-..."
              helperText={t("storedPlaintext")}
            />
            <button
              type="button"
              className="absolute right-3 top-9 text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
              onClick={() => setShowKey((v) => !v)}
              title={showKey ? t("hide") : t("show")}
            >
              {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">{t("models")}</label>
            <textarea
              value={modelsJson}
              onChange={(e) => setModelsJson(e.target.value)}
              className={cn(
                "w-full min-h-[220px] font-mono text-xs",
                "border border-gray-300 dark:border-gray-600 rounded-md",
                "bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100",
                "px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              )}
              placeholder={JSON.stringify({ models: DEFAULT_OPENROUTER_MODELS_EXAMPLE.providers.openrouter.models }, null, 2)}
            />
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Paste JSON in the form: <code>{"{ models: [...] }"}</code>. Each model can include id/name/reasoning/cost/contextWindow/maxTokens.
            </div>
          </div>

          {localError && (
            <div className="flex items-center gap-2 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" />
              {localError}
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={async () => {
                setLocalError(null);
                setSavedOk(false);

                let parsed: unknown = null;
                try {
                  parsed = modelsJson ? (JSON.parse(modelsJson) as unknown) : ({ models: [] } as unknown);
                } catch {
                  setLocalError(t("modelsInvalid"));
                  return;
                }

                const models =
                  parsed && typeof parsed === "object" && (parsed as Record<string, unknown>).models
                    ? (parsed as Record<string, unknown>).models
                    : null;
                if (!Array.isArray(models)) {
                  setLocalError(t("modelsObjectRequired"));
                  return;
                }

                await upsert.mutateAsync({
                  apiKey,
                  config: {
                    provider,
                    baseUrl,
                    api: "openai-responses",
                    auth: "api-key",
                    models,
                  },
                });

                setSavedOk(true);
                setTimeout(() => setSavedOk(false), 1500);
              }}
              disabled={upsert.isPending}
              className={cn(
                "inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium",
                "bg-blue-600 hover:bg-blue-700 text-white",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              {upsert.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {t("save")}
            </button>

            {savedOk && (
              <div className="flex items-center gap-1 text-sm text-green-700 dark:text-green-400">
                <Check className="h-4 w-4" />
                {t("saved")}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
