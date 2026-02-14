/**
 * Session Tab Bar Component
 *
 * Horizontal tabs for session management with:
 * - Drag and drop reordering (visualize research workflow)
 * - Double-click to rename
 * - Right-click context menu (rename, delete)
 * - Click to switch session
 * - "+" button to create new session
 */

"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  horizontalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Plus, X, GripVertical, ChevronDown, ChevronUp, Copy, Pencil, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils/cn";

export interface Session {
  id: string;
  title: string;
  created_at?: string;
  updated_at?: string;
}

interface SessionTabBarProps {
  sessions: Session[];
  currentSessionId: string | null;
  onSessionSelect: (sessionId: string) => void;
  onSessionCreate: () => void;
  onSessionRename: (sessionId: string, newTitle: string) => void;
  onSessionDelete: (sessionId: string) => void;
  onSessionDuplicate: (sessionId: string) => void;
  onSessionReorder: (sessions: Session[]) => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

// Individual sortable tab
function SortableTab({
  session,
  isActive,
  onSelect,
  onRename,
  onDelete,
  onDuplicate,
}: {
  session: Session;
  isActive: boolean;
  onSelect: () => void;
  onRename: (newTitle: string) => void;
  onDelete: () => void;
  onDuplicate: () => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(session.title);
  const [showContextMenu, setShowContextMenu] = useState(false);
  const [contextMenuPos, setContextMenuPos] = useState({ x: 0, y: 0 });
  const inputRef = useRef<HTMLInputElement>(null);

  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: session.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 100 : undefined,
  };

  // Focus input when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditing]);

  // Close context menu on click outside
  useEffect(() => {
    const handleClick = () => setShowContextMenu(false);
    if (showContextMenu) {
      document.addEventListener("click", handleClick);
      return () => document.removeEventListener("click", handleClick);
    }
  }, [showContextMenu]);

  const handleDoubleClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setEditValue(session.title);
    setIsEditing(true);
  };

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenuPos({ x: e.clientX, y: e.clientY });
    setShowContextMenu(true);
  };

  const handleEditSubmit = () => {
    if (editValue.trim() && editValue !== session.title) {
      onRename(editValue.trim());
    }
    setIsEditing(false);
  };

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleEditSubmit();
    } else if (e.key === "Escape") {
      setIsEditing(false);
      setEditValue(session.title);
    }
  };

  return (
    <>
      <div
        ref={setNodeRef}
        style={style}
        className={cn(
          "flex items-center gap-1 px-3 py-1.5 rounded-t-md border border-b-0 cursor-pointer",
          "transition-all duration-150 select-none min-w-[100px] max-w-[200px]",
          isActive
            ? "bg-white dark:bg-gray-900 border-gray-300 dark:border-gray-700 shadow-sm"
            : "bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700",
          isDragging && "opacity-50 shadow-lg"
        )}
        onClick={onSelect}
        onDoubleClick={handleDoubleClick}
        onContextMenu={handleContextMenu}
      >
        {/* Drag handle */}
        <span
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing text-gray-400 hover:text-gray-600"
        >
          <GripVertical className="h-3 w-3" />
        </span>

        {/* Title or edit input */}
        {isEditing ? (
          <input
            ref={inputRef}
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={handleEditSubmit}
            onKeyDown={handleEditKeyDown}
            className="flex-1 text-sm bg-transparent border-none outline-none px-1 min-w-0"
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="flex-1 text-sm truncate" title={session.title}>
            {session.title}
          </span>
        )}

        {/* Close button (only on active tab) */}
        {isActive && (
          <button
            className="p-0.5 rounded hover:bg-gray-200 text-gray-400 hover:text-gray-600"
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            title="Close session"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>

      {/* Context menu */}
      {showContextMenu && (
        <div
          className="fixed bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-md shadow-lg py-1 z-50"
          style={{ left: contextMenuPos.x, top: contextMenuPos.y }}
        >
          <button
            className="w-full px-4 py-1.5 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-900 dark:text-gray-100 flex items-center gap-2"
            onClick={() => {
              setShowContextMenu(false);
              setEditValue(session.title);
              setIsEditing(true);
            }}
          >
            <Pencil className="h-3.5 w-3.5" />
            Rename
          </button>
          <button
            className="w-full px-4 py-1.5 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-900 dark:text-gray-100 flex items-center gap-2"
            onClick={() => {
              setShowContextMenu(false);
              onDuplicate();
            }}
          >
            <Copy className="h-3.5 w-3.5" />
            Duplicate
          </button>
          <div className="border-t border-gray-200 dark:border-gray-700 my-1" />
          <button
            className="w-full px-4 py-1.5 text-sm text-left hover:bg-gray-100 dark:hover:bg-gray-800 text-red-600 flex items-center gap-2"
            onClick={() => {
              setShowContextMenu(false);
              onDelete();
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </button>
        </div>
      )}
    </>
  );
}

export function SessionTabBar({
  sessions,
  currentSessionId,
  onSessionSelect,
  onSessionCreate,
  onSessionRename,
  onSessionDelete,
  onSessionDuplicate,
  onSessionReorder,
  collapsed = false,
  onToggleCollapse,
}: SessionTabBarProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px movement before drag starts
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      const oldIndex = sessions.findIndex((s) => s.id === active.id);
      const newIndex = sessions.findIndex((s) => s.id === over.id);
      const newSessions = arrayMove(sessions, oldIndex, newIndex);
      onSessionReorder(newSessions);
    }
  };

  if (collapsed) {
    return (
      <button
        onClick={onToggleCollapse}
        className="flex items-center justify-center gap-1.5 w-full px-3 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
      >
        <ChevronDown className="h-5 w-5 text-gray-700 dark:text-gray-200" />
        <span className="text-xs font-semibold text-gray-700 dark:text-gray-200 tracking-wide uppercase">Sessions</span>
      </button>
    );
  }

  return (
    <div className="flex items-end gap-1 px-2 pt-1 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={sessions.map((s) => s.id)}
          strategy={horizontalListSortingStrategy}
        >
          {sessions.map((session) => (
            <SortableTab
              key={session.id}
              session={session}
              isActive={session.id === currentSessionId}
              onSelect={() => onSessionSelect(session.id)}
              onRename={(newTitle) => onSessionRename(session.id, newTitle)}
              onDelete={() => onSessionDelete(session.id)}
              onDuplicate={() => onSessionDuplicate(session.id)}
            />
          ))}
        </SortableContext>
      </DndContext>

      {/* New session button */}
      <button
        className={cn(
          "flex items-center justify-center w-8 h-8 rounded-t-md",
          "bg-gray-100 dark:bg-gray-800 border border-b-0 border-gray-200 dark:border-gray-700",
          "hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        )}
        onClick={onSessionCreate}
        title="New Session"
      >
        <Plus className="h-4 w-4 text-gray-600 dark:text-gray-200" />
      </button>

      {/* Spacer to push tabs left */}
      <div className="flex-1" />

      {/* Collapse button */}
      {onToggleCollapse && (
        <button
          onClick={onToggleCollapse}
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500 mb-1"
          title="Collapse sessions"
        >
          <ChevronUp className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}
