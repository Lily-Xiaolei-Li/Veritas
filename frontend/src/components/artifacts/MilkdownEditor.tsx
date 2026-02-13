/**
 * MilkdownEditor Component
 * 
 * WYSIWYG Markdown editor using Milkdown.
 * Supports tables, formatting, and real-time markdown sync.
 * Includes context menu for AI features.
 */

"use client";

import React, { useEffect, useRef, useCallback, useState } from "react";
import { Editor, rootCtx, defaultValueCtx, editorViewCtx } from "@milkdown/kit/core";
import { commonmark } from "@milkdown/kit/preset/commonmark";
import { gfm } from "@milkdown/preset-gfm";
import { listener, listenerCtx } from "@milkdown/plugin-listener";
import { Milkdown, MilkdownProvider, useEditor } from "@milkdown/react";
import { replaceAll } from "@milkdown/utils";
import { highlightPlugins } from "./milkdown-highlight";

// Styles for the editor
const editorStyles = `
  .milkdown {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #1f2937;
    padding: 16px;
    min-height: 100%;
    outline: none;
  }
  
  .dark .milkdown {
    color: #f3f4f6;
  }
  
  .milkdown .editor {
    outline: none;
  }
  
  .milkdown p {
    margin: 0 0 1em 0;
  }
  
  .milkdown h1 {
    font-size: 1.875rem;
    font-weight: 700;
    margin: 1.5em 0 0.5em 0;
    color: #111827;
  }
  
  .milkdown h2 {
    font-size: 1.5rem;
    font-weight: 600;
    margin: 1.25em 0 0.5em 0;
    color: #1f2937;
  }
  
  .milkdown h3 {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 1em 0 0.5em 0;
    color: #374151;
  }
  
  .dark .milkdown h1,
  .dark .milkdown h2,
  .dark .milkdown h3 {
    color: #f9fafb;
  }
  
  .milkdown strong {
    font-weight: 700;
  }
  
  .milkdown em {
    font-style: italic;
  }
  
  .milkdown mark {
    background-color: #fef08a;
    padding: 0 2px;
    border-radius: 2px;
  }
  
  .dark .milkdown mark {
    background-color: #854d0e;
    color: #fef9c3;
  }
  
  .milkdown del {
    text-decoration: line-through;
    color: #9ca3af;
  }
  
  .dark .milkdown del {
    color: #6b7280;
  }
  
  .milkdown code {
    background-color: #f3f4f6;
    padding: 0.125em 0.25em;
    border-radius: 0.25rem;
    font-family: ui-monospace, monospace;
    font-size: 0.875em;
  }
  
  .dark .milkdown code {
    background-color: #374151;
  }
  
  .milkdown pre {
    background-color: #1f2937;
    color: #f3f4f6;
    padding: 1em;
    border-radius: 0.5rem;
    overflow-x: auto;
    margin: 1em 0;
  }
  
  .milkdown pre code {
    background: none;
    padding: 0;
    color: inherit;
  }
  
  .milkdown blockquote {
    border-left: 4px solid #d1d5db;
    padding-left: 1em;
    margin: 1em 0;
    color: #6b7280;
    font-style: italic;
  }
  
  .dark .milkdown blockquote {
    border-left-color: #4b5563;
    color: #9ca3af;
  }
  
  .milkdown ul, .milkdown ol {
    margin: 0.5em 0;
    padding-left: 1.5em;
  }
  
  .milkdown li {
    margin: 0.25em 0;
  }
  
  .milkdown hr {
    border: none;
    border-top: 2px solid #e5e7eb;
    margin: 1.5em 0;
  }
  
  .dark .milkdown hr {
    border-top-color: #4b5563;
  }
  
  .milkdown a {
    color: #2563eb;
    text-decoration: underline;
  }
  
  .dark .milkdown a {
    color: #60a5fa;
  }
  
  /* Table styles */
  .milkdown table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
  }
  
  .milkdown th, .milkdown td {
    border: 1px solid #d1d5db;
    padding: 0.5em 0.75em;
    text-align: left;
  }
  
  .milkdown th {
    background-color: #f3f4f6;
    font-weight: 600;
  }
  
  .dark .milkdown th {
    background-color: #374151;
  }
  
  .dark .milkdown th, .dark .milkdown td {
    border-color: #4b5563;
  }
  
  /* Task list */
  .milkdown .task-list-item {
    list-style: none;
    margin-left: -1.5em;
  }
  
  .milkdown .task-list-item input {
    margin-right: 0.5em;
  }
`;

export interface MilkdownEditorProps {
  initialValue: string;
  onChange: (markdown: string) => void;
  onTogglePrompting?: (selectedText: string) => void;
  onToggleEditing?: (selectedText: string) => void;
  onCreateArtifact?: (selectedText: string) => void;
  onHighlight?: (selectedText: string) => void;
}

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  selectedText: string;
}

function MilkdownEditorInner({ 
  initialValue, 
  onChange,
  onTogglePrompting,
  onToggleEditing,
  onCreateArtifact,
  onHighlight,
}: MilkdownEditorProps) {
  const initialValueRef = useRef(initialValue);
  const onChangeRef = useRef(onChange);
  const containerRef = useRef<HTMLDivElement>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    selectedText: "",
  });
  
  // Keep onChange ref updated
  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  const { get } = useEditor((root) => {
    return Editor.make()
      .config((ctx) => {
        ctx.set(rootCtx, root);
        ctx.set(defaultValueCtx, initialValueRef.current);
        
        // Set up listener for changes
        ctx.get(listenerCtx).markdownUpdated((_, markdown) => {
          onChangeRef.current(markdown);
        });
      })
      .use(commonmark)
      .use(gfm)
      .use(highlightPlugins)
      .use(listener);
  }, []);

  // Update content when initialValue changes externally
  useEffect(() => {
    const editor = get();
    if (editor && initialValue !== initialValueRef.current) {
      initialValueRef.current = initialValue;
      editor.action(replaceAll(initialValue));
    }
  }, [initialValue, get]);

  // Get selected text from ProseMirror
  const getSelectedText = useCallback(() => {
    const editor = get();
    if (!editor) return "";
    
    try {
      const view = editor.ctx.get(editorViewCtx);
      const { from, to } = view.state.selection;
      if (from === to) return "";
      return view.state.doc.textBetween(from, to, " ");
    } catch {
      // Fallback to window selection
      const selection = window.getSelection();
      return selection?.toString() || "";
    }
  }, [get]);

  // Handle right-click
  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const selectedText = getSelectedText();
    
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      selectedText,
    });
  }, [getSelectedText]);

  // Close context menu
  const closeMenu = useCallback(() => {
    setContextMenu(prev => ({ ...prev, visible: false }));
  }, []);

  // Close menu on click outside
  useEffect(() => {
    const handleClick = () => closeMenu();
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, [closeMenu]);

  // Menu item component
  const MenuItem = ({ label, onClick, disabled }: { label: string; onClick: () => void; disabled?: boolean }) => (
    <div
      onClick={(e) => {
        e.stopPropagation();
        if (!disabled) {
          onClick();
          closeMenu();
        }
      }}
      className={`px-3 py-1.5 text-sm cursor-pointer ${
        disabled
          ? "text-gray-400 dark:text-gray-500 cursor-not-allowed"
          : "text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
      }`}
    >
      {label}
    </div>
  );

  const Divider = () => (
    <div className="border-t border-gray-200 dark:border-gray-600 my-1" />
  );

  const hasSelection = contextMenu.selectedText.length > 0;

  return (
    <div ref={containerRef} onContextMenu={handleContextMenu} className="h-full">
      <style>{editorStyles}</style>
      <Milkdown />
      
      {/* Context Menu */}
      {contextMenu.visible && (
        <div
          className="fixed z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-md shadow-lg py-1 min-w-[200px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <MenuItem
            label="📌 Toggle for prompting"
            onClick={() => onTogglePrompting?.(contextMenu.selectedText)}
            disabled={!hasSelection}
          />
          <MenuItem
            label="🎯 Toggle for editing"
            onClick={() => onToggleEditing?.(contextMenu.selectedText)}
            disabled={!hasSelection}
          />
          <MenuItem
            label="📄 Create new artifact"
            onClick={() => onCreateArtifact?.(contextMenu.selectedText)}
            disabled={!hasSelection}
          />
          <MenuItem
            label="🟡 Highlight"
            onClick={() => onHighlight?.(contextMenu.selectedText)}
            disabled={!hasSelection}
          />
          
          <Divider />
          
          <MenuItem
            label="📋 Copy"
            onClick={() => {
              if (contextMenu.selectedText) {
                navigator.clipboard.writeText(contextMenu.selectedText);
              }
            }}
            disabled={!hasSelection}
          />
        </div>
      )}
    </div>
  );
}

export default function MilkdownEditor(props: MilkdownEditorProps) {
  return (
    <MilkdownProvider>
      <MilkdownEditorInner {...props} />
    </MilkdownProvider>
  );
}
