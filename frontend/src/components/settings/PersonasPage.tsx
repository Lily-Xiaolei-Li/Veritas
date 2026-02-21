"use client";

import React, { useMemo, useState } from "react";
import { Plus, Trash2, Save, GripVertical } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils/cn";
import { usePersonas, useCreatePersona, useUpdatePersona, useDeletePersona } from "@/lib/hooks/usePersonas";
import { useReorderPersonas } from "@/lib/hooks/usePersonaReorder";
import type { Persona } from "@/lib/personas/registry";

export function PersonasPage() {
  const t = useTranslations("personas");
  const { data, isLoading, isError, error } = usePersonas();
  const createMutation = useCreatePersona();
  const updateMutation = useUpdatePersona();
  const deleteMutation = useDeletePersona();
  const reorderMutation = useReorderPersonas();

  const personas = useMemo(
    () => (data?.personas ?? []).slice().sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)),
    [data?.personas]
  );

  const [dragId, setDragId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);
  const [overPos, setOverPos] = useState<"above" | "below" | null>(null);

  const [draftId, setDraftId] = useState("");
  const [draftLabel, setDraftLabel] = useState("");
  const [draftPrompt, setDraftPrompt] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState("");
  const [editPrompt, setEditPrompt] = useState("");

  const startEdit = (p: Persona) => {
    setEditingId(p.id);
    setEditLabel(p.label);
    setEditPrompt(p.system_prompt);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditLabel("");
    setEditPrompt("");
  };

  const saveEdit = async () => {
    if (!editingId) return;
    await updateMutation.mutateAsync({
      id: editingId,
      label: editLabel.trim() || undefined,
      system_prompt: editPrompt.trim() || undefined,
    });
    cancelEdit();
  };

  const create = async () => {
    await createMutation.mutateAsync({
      id: draftId.trim(),
      label: draftLabel.trim(),
      system_prompt: draftPrompt.trim(),
    });
    setDraftId("");
    setDraftLabel("");
    setDraftPrompt("");
  };

  const remove = async (id: string) => {
    const ok = confirm(t("deleteConfirm", { id }));
    if (!ok) return;
    await deleteMutation.mutateAsync(id);
    if (editingId === id) cancelEdit();
  };

  const busy =
    createMutation.isPending ||
    updateMutation.isPending ||
    deleteMutation.isPending ||
    reorderMutation.isPending;

  const applyReorder = async (fromId: string, toId: string, position: "above" | "below") => {
    const ids = personas.map((p) => p.id);
    const fromIdx = ids.indexOf(fromId);
    const toIdx = ids.indexOf(toId);
    if (fromIdx === -1 || toIdx === -1 || fromIdx === toIdx) return;

    // remove from original position
    ids.splice(fromIdx, 1);

    // compute insert index after removal
    const toIdxAfter = ids.indexOf(toId);
    if (toIdxAfter === -1) return;

    const insertAt = position === "above" ? toIdxAfter : toIdxAfter + 1;
    ids.splice(insertAt, 0, fromId);

    await reorderMutation.mutateAsync(ids);
  };
  return (
    <div className="p-4 space-y-6">
      <div>
        <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">{t("title")}</div>
        <div className="text-sm text-gray-600 dark:text-gray-300 mt-1">
          {t("description")}
        </div>
      </div>

      {/* Create */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-900">
        <div className="flex items-center gap-2 mb-3">
          <Plus className="h-4 w-4 text-blue-600" />
          <div className="font-medium text-gray-900 dark:text-gray-100">{t("addPersona")}</div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
              ID (stable key)
            </label>
            <input
              value={draftId}
              onChange={(e) => setDraftId(e.target.value)}
              placeholder={t("idPlaceholder")}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100"
              disabled={busy}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
              Label
            </label>
            <input
              value={draftLabel}
              onChange={(e) => setDraftLabel(e.target.value)}
              placeholder={t("labelPlaceholder")}
              className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100"
              disabled={busy}
            />
          </div>
        </div>

        <div className="mt-3">
          <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
            System Prompt
          </label>
          <textarea
            value={draftPrompt}
            onChange={(e) => setDraftPrompt(e.target.value)}
            placeholder={t("promptPlaceholder")}
            className="w-full min-h-[120px] px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100"
            disabled={busy}
          />
        </div>

        <div className="mt-3 flex justify-end">
          <button
            type="button"
            onClick={() => void create()}
            disabled={busy || !draftId.trim() || !draftLabel.trim() || !draftPrompt.trim()}
            className={cn(
              "inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded",
              "bg-blue-600 hover:bg-blue-700 text-white",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            <Save className="h-4 w-4" />
            Create
          </button>
        </div>

        {createMutation.isError && (
          <div className="mt-2 text-xs text-red-600">{(createMutation.error as Error).message}</div>
        )}
      </div>

      {/* List */}
      <div className="space-y-3">
        <div className="text-sm font-medium text-gray-800 dark:text-gray-200">
          Existing personas ({personas.length})
        </div>

        {isLoading && <div className="text-sm text-gray-500">{t("loading")}</div>}
        {isError && (
          <div className="text-sm text-red-600">
            Failed to load personas: {(error as Error)?.message}
          </div>
        )}

        {!isLoading && !isError && personas.length === 0 && (
          <div className="text-sm text-gray-500">{t("empty")}</div>
        )}

        {personas.map((p) => {
          const isEditing = editingId === p.id;
          const isOver = overId === p.id && dragId && dragId !== p.id;
          const showAbove = isOver && overPos === "above";
          const showBelow = isOver && overPos === "below";
          return (
            <div
              key={p.id}
              onDragOver={(e) => {
                e.preventDefault();
                if (!dragId || dragId === p.id) return;

                const rect = (e.currentTarget as HTMLDivElement).getBoundingClientRect();
                const mid = rect.top + rect.height / 2;
                const pos = e.clientY < mid ? "above" : "below";
                setOverId(p.id);
                setOverPos(pos);
              }}
              onDragLeave={() => {
                if (overId === p.id) {
                  setOverId(null);
                  setOverPos(null);
                }
              }}
              onDrop={(e) => {
                e.preventDefault();
                const dragged =
                  dragId ||
                  (() => {
                    try {
                      return e.dataTransfer.getData("text/plain") || null;
                    } catch {
                      return null;
                    }
                  })();

                if (dragged && dragged !== p.id && overPos) {
                  void applyReorder(dragged, p.id, overPos);
                }

                setDragId(null);
                setOverId(null);
                setOverPos(null);
              }}
              className={cn(
                "relative border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-900",
                "select-none",
                isOver && "ring-1 ring-blue-500/40"
              )}
              title={t("dragHandleToReorder")}
            >
              {/* Insertion line hints */}
              {showAbove && (
                <div className="absolute left-2 right-2 -top-1 h-0.5 bg-blue-500 rounded" />
              )}
              {showBelow && (
                <div className="absolute left-2 right-2 -bottom-1 h-0.5 bg-blue-500 rounded" />
              )}

              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2 min-w-0">
                  {/* Drag handle */}
                  <button
                    type="button"
                    draggable
                    onDragStart={(e) => {
                      // NOTE: Some browsers require setData for drag events to properly fire drop.
                      e.dataTransfer.effectAllowed = "move";
                      try {
                        e.dataTransfer.setData("text/plain", p.id);
                      } catch {
                        // ignore
                      }
                      setDragId(p.id);
                    }}
                    onDragEnd={() => {
                      setDragId(null);
                      setOverId(null);
                      setOverPos(null);
                    }}
                    className={cn(
                      "mt-0.5 p-1 rounded",
                      "text-gray-400 hover:text-gray-200",
                      "hover:bg-gray-800/40",
                      busy && "opacity-50 cursor-not-allowed"
                    )}
                    disabled={busy}
                    title={t("dragToReorder")}
                    aria-label={t("dragToReorder")}
                  >
                    <GripVertical className="h-4 w-4" />
                  </button>

                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
                      {p.label}
                    </div>
                    <div className="text-xs text-gray-500 dark:text-gray-400">id: {p.id}</div>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {!isEditing ? (
                    <button
                      type="button"
                      onClick={() => startEdit(p)}
                      className="px-2.5 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800"
                      disabled={busy}
                    >
                      Edit
                    </button>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={cancelEdit}
                        className="px-2.5 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800"
                        disabled={busy}
                      >
                        Cancel
                      </button>
                      <button
                        type="button"
                        onClick={() => void saveEdit()}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50"
                        disabled={busy || !editLabel.trim() || !editPrompt.trim()}
                      >
                        <Save className="h-3.5 w-3.5" />
                        Save
                      </button>
                    </>
                  )}

                  <button
                    type="button"
                    onClick={() => void remove(p.id)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded border border-red-300 text-red-700 hover:bg-red-50 disabled:opacity-50"
                    disabled={busy}
                    title={t("deletePersona")}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Delete
                  </button>
                </div>
              </div>

              <div className="mt-3">
                <label className="block text-xs font-medium text-gray-600 dark:text-gray-300 mb-1">
                  System Prompt
                </label>
                {isEditing ? (
                  <>
                    <input
                      value={editLabel}
                      onChange={(e) => setEditLabel(e.target.value)}
                      className="w-full mb-2 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100"
                      disabled={busy}
                    />
                    <textarea
                      value={editPrompt}
                      onChange={(e) => setEditPrompt(e.target.value)}
                      className="w-full min-h-[120px] px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100"
                      disabled={busy}
                    />
                  </>
                ) : (
                  <div className="text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-700 rounded p-2 text-gray-800 dark:text-gray-200 max-h-40 overflow-auto">
                    {p.system_prompt}
                  </div>
                )}
              </div>

              {updateMutation.isError && isEditing && (
                <div className="mt-2 text-xs text-red-600">{(updateMutation.error as Error).message}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
