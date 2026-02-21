/**
 * Settings Modal Component (B1.6 - Authentication & API Key UI)
 *
 * Modal for accessing application settings:
 * - API Keys management
 * - Future: User preferences (B3.3)
 */

"use client";

import React, { useState } from "react";
import { Key, Settings as SettingsIcon, Theater } from "lucide-react";
import { useTranslations } from "next-intl";
import { Modal } from "@/components/ui/Modal";
import { ApiKeysPage } from "./ApiKeysPage";
import { PreferencesPage } from "./PreferencesPage";
import { PersonasPage } from "./PersonasPage";
import { cn } from "@/lib/utils/cn";

// =============================================================================
// Types
// =============================================================================

type SettingsTab = "llm-providers" | "preferences" | "personas";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface TabConfig {
  id: SettingsTab;
  label: string;
  icon: React.ReactNode;
}

// =============================================================================
// Constants
// =============================================================================

const TABS: TabConfig[] = [
  {
    id: "llm-providers",
    label: "settings.llmProviders",
    icon: <Key className="h-4 w-4" />,
  },
  {
    id: "preferences",
    label: "settings.preferences",
    icon: <SettingsIcon className="h-4 w-4" />,
  },
  {
    id: "personas",
    label: "settings.personas",
    icon: <Theater className="h-4 w-4" />,
  },
];

// =============================================================================
// Component
// =============================================================================

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const t = useTranslations();
  const [activeTab, setActiveTab] = useState<SettingsTab>("llm-providers");

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t("settings.title")}
      size="xl"
      className="max-h-[80vh] flex flex-col"
    >
      <div className="flex flex-1 min-h-0 -mx-6 -mb-4">
        {/* Sidebar */}
        <div className="w-48 flex-shrink-0 border-r border-gray-200 dark:border-gray-700 py-2 bg-white dark:bg-gray-900">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "w-full flex items-center gap-2 px-4 py-2 text-left text-sm",
                "transition-colors",
                activeTab === tab.id
                  ? "bg-blue-50 text-blue-700 border-r-2 border-blue-600"
                  : "text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800"
              )}
            >
              {tab.icon}
              {t(tab.label)}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === "llm-providers" && <ApiKeysPage />}
          {activeTab === "preferences" && <PreferencesPage />}
          {activeTab === "personas" && <PersonasPage />}
        </div>
      </div>
    </Modal>
  );
}

// =============================================================================
// Settings Button
// =============================================================================

interface SettingsButtonProps {
  onClick: () => void;
  className?: string;
}

export function SettingsButton({ onClick, className }: SettingsButtonProps) {
  const t = useTranslations();
  return (
    <button
      onClick={onClick}
      className={cn(
        "p-2 text-gray-500 hover:text-gray-700",
        "hover:bg-gray-100 rounded-md transition-colors",
        "focus:outline-none focus:ring-2 focus:ring-blue-500",
        className
      )}
      aria-label={t("settings.title")}
    >
      <SettingsIcon className="h-5 w-5" />
    </button>
  );
}
