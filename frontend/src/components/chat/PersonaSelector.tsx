/**
 * PersonaSelector Component
 *
 * Dropdown selector for academic personas.
 * Each persona has a specific system prompt that shapes the AI's behavior.
 */

"use client";

import React, { useEffect } from "react";
import { User } from "lucide-react";
import {
  type Persona,
  DEFAULT_PERSONAS as ACADEMIC_PERSONAS,
  getPersonaById,
  setPersonas,
} from "@/lib/personas/registry";
import { usePersonas } from "@/lib/hooks/usePersonas";

export type { Persona };
export { ACADEMIC_PERSONAS, getPersonaById };

interface PersonaSelectorProps {
  selectedPersonaId: string;
  onSelect: (personaId: string) => void;
  disabled?: boolean;
}

export function PersonaSelector({ selectedPersonaId, onSelect, disabled = false }: PersonaSelectorProps) {
  const { data } = usePersonas();

  // Keep registry synced so other panels can resolve persona prompts.
  useEffect(() => {
    if (data?.personas) {
      setPersonas(data.personas);
    }
  }, [data?.personas]);

  const personas = (data?.personas?.length ? data.personas : ACADEMIC_PERSONAS)
    .slice()
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
  const selectedPersona = personas.find((p) => p.id === selectedPersonaId) || personas[0];

  return (
    <div className="flex items-center gap-2">
      <User className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
      <select
        value={selectedPersonaId}
        onChange={(e) => onSelect(e.target.value)}
        disabled={disabled}
        className="text-xs border border-gray-300 dark:border-gray-600 rounded px-2 py-1 bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 disabled:opacity-50 disabled:cursor-not-allowed min-w-[140px]"
        title={selectedPersona.system_prompt}
      >
        {personas.map((persona) => (
          <option key={persona.id} value={persona.id}>
            {persona.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// getPersonaById re-exported from registry
