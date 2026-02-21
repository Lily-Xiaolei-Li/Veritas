/**
 * Application Providers
 *
 * Client-side providers for React Query and other global state.
 */

"use client";

import React, { useEffect, useMemo } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeApplier } from "@/components/ui/ThemeApplier";
import { NextIntlClientProvider } from "next-intl";
import enMessages from "../../messages/en.json";
import zhMessages from "../../messages/zh.json";
import { useWorkbenchStore } from "@/lib/store";
import { defaultLocale, isLocale, type Locale } from "@/i18n/config";

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function Providers({ children }: { children: React.ReactNode }) {
  const locale = useWorkbenchStore((s) => s.locale);
  const setLocale = useWorkbenchStore((s) => s.setLocale);

  useEffect(() => {
    try {
      const persisted = localStorage.getItem("agentb:locale");
      if (persisted && isLocale(persisted)) {
        setLocale(persisted as Locale);
      }
    } catch {
      setLocale(defaultLocale);
    }
  }, [setLocale]);

  const messages = useMemo(() => (locale === "zh" ? zhMessages : enMessages), [locale]);

  return (
    <QueryClientProvider client={queryClient}>
      <NextIntlClientProvider locale={locale} messages={messages}>
        <ThemeApplier />
        {children}
      </NextIntlClientProvider>
    </QueryClientProvider>
  );
}
