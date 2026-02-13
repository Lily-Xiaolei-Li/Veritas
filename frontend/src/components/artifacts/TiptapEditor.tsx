/**
 * TiptapEditor Component
 * 
 * Full-featured WYSIWYG Markdown editor using Tiptap.
 * Supports formatting, colors, images, links, mentions, and more.
 */

"use client";

import React, { useEffect, useCallback, useState, useRef } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Highlight from "@tiptap/extension-highlight";
import Typography from "@tiptap/extension-typography";
import Placeholder from "@tiptap/extension-placeholder";
import { Table } from "@tiptap/extension-table";
import { TableRow } from "@tiptap/extension-table-row";
import { TableCell } from "@tiptap/extension-table-cell";
import { TableHeader } from "@tiptap/extension-table-header";
import { Color } from "@tiptap/extension-color";
import { TextStyle } from "@tiptap/extension-text-style";
import { Underline } from "@tiptap/extension-underline";
import CharacterCount from "@tiptap/extension-character-count";
import TextAlign from "@tiptap/extension-text-align";
import Link from "@tiptap/extension-link";
import Image from "@tiptap/extension-image";
import Youtube from "@tiptap/extension-youtube";
import Superscript from "@tiptap/extension-superscript";
import Subscript from "@tiptap/extension-subscript";
import Focus from "@tiptap/extension-focus";
import { marked } from "marked";
import TurndownService from "turndown";

// Configure marked for GFM
marked.use({
  gfm: true,
  breaks: false,
});

// Configure turndown for markdown output
const turndownService = new TurndownService({
  headingStyle: "atx",
  codeBlockStyle: "fenced",
  bulletListMarker: "-",
});

// Add table support to turndown
turndownService.addRule("table", {
  filter: "table",
  replacement: function (content, node) {
    const table = node as HTMLTableElement;
    const rows = Array.from(table.rows);
    if (rows.length === 0) return content;

    let markdown = "\n";
    rows.forEach((row, rowIndex) => {
      const cells = Array.from(row.cells);
      const cellContents = cells.map((cell) => cell.textContent?.trim() || "");
      markdown += "| " + cellContents.join(" | ") + " |\n";
      if (rowIndex === 0) {
        markdown += "| " + cells.map(() => "---").join(" | ") + " |\n";
      }
    });
    return markdown + "\n";
  },
});

// Add highlight/mark support to turndown
turndownService.addRule("mark", {
  filter: "mark",
  replacement: function (content) {
    return "==" + content + "==";
  },
});

// Add superscript support
turndownService.addRule("sup", {
  filter: "sup",
  replacement: function (content) {
    return "^" + content + "^";
  },
});

// Add subscript support
turndownService.addRule("sub", {
  filter: "sub",
  replacement: function (content) {
    return "~" + content + "~";
  },
});

// Highlight colors
const HIGHLIGHT_COLORS = [
  { name: "Yellow", color: "#fef08a" },
  { name: "Green", color: "#bbf7d0" },
  { name: "Blue", color: "#bfdbfe" },
  { name: "Pink", color: "#fbcfe8" },
  { name: "Orange", color: "#fed7aa" },
  { name: "Purple", color: "#e9d5ff" },
  { name: "None", color: null },
];

// Text colors
const TEXT_COLORS = [
  { name: "Default", color: null },
  { name: "Red", color: "#dc2626" },
  { name: "Orange", color: "#ea580c" },
  { name: "Green", color: "#16a34a" },
  { name: "Blue", color: "#2563eb" },
  { name: "Purple", color: "#9333ea" },
  { name: "Gray", color: "#6b7280" },
];

// Editor styles
const editorStyles = `
  .tiptap-editor {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #1f2937;
    padding: 16px;
    min-height: calc(100% - 80px);
    outline: none;
  }
  
  .dark .tiptap-editor {
    color: #f3f4f6;
  }
  
  .tiptap-editor:focus {
    outline: none;
  }
  
  .tiptap-editor p {
    margin: 0 0 1em 0;
  }
  
  .tiptap-editor h1 {
    font-size: 1.875rem;
    font-weight: 700;
    margin: 1.5em 0 0.5em 0;
    color: #111827;
  }
  
  .tiptap-editor h2 {
    font-size: 1.5rem;
    font-weight: 600;
    margin: 1.25em 0 0.5em 0;
    color: #1f2937;
  }
  
  .tiptap-editor h3 {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 1em 0 0.5em 0;
    color: #374151;
  }
  
  .dark .tiptap-editor h1,
  .dark .tiptap-editor h2,
  .dark .tiptap-editor h3 {
    color: #f9fafb;
  }
  
  .tiptap-editor strong {
    font-weight: 700;
  }
  
  .tiptap-editor em {
    font-style: italic;
  }
  
  .tiptap-editor u {
    text-decoration: underline;
  }
  
  .tiptap-editor sup {
    vertical-align: super;
    font-size: 0.75em;
  }
  
  .tiptap-editor sub {
    vertical-align: sub;
    font-size: 0.75em;
  }
  
  .tiptap-editor mark {
    background-color: #fef08a;
    padding: 0 2px;
    border-radius: 2px;
  }
  
  .dark .tiptap-editor mark {
    background-color: #854d0e;
    color: #fef9c3;
  }
  
  .tiptap-editor code {
    background-color: #f3f4f6;
    padding: 0.125em 0.25em;
    border-radius: 0.25rem;
    font-family: ui-monospace, monospace;
    font-size: 0.875em;
  }
  
  .dark .tiptap-editor code {
    background-color: #374151;
  }
  
  .tiptap-editor pre {
    background-color: #1f2937;
    color: #f3f4f6;
    padding: 1em;
    border-radius: 0.5rem;
    overflow-x: auto;
    margin: 1em 0;
  }
  
  .tiptap-editor pre code {
    background: none;
    padding: 0;
    color: inherit;
  }
  
  .tiptap-editor blockquote {
    border-left: 4px solid #d1d5db;
    padding-left: 1em;
    margin: 1em 0;
    color: #6b7280;
    font-style: italic;
  }
  
  .dark .tiptap-editor blockquote {
    border-left-color: #4b5563;
    color: #9ca3af;
  }
  
  .tiptap-editor ul, .tiptap-editor ol {
    margin: 0.5em 0;
    padding-left: 1.5em;
  }
  
  .tiptap-editor li {
    margin: 0.25em 0;
  }
  
  .tiptap-editor hr {
    border: none;
    border-top: 2px solid #e5e7eb;
    margin: 1.5em 0;
  }
  
  .dark .tiptap-editor hr {
    border-top-color: #4b5563;
  }
  
  .tiptap-editor a {
    color: #2563eb;
    text-decoration: underline;
    cursor: pointer;
  }
  
  .dark .tiptap-editor a {
    color: #60a5fa;
  }
  
  .tiptap-editor s {
    text-decoration: line-through;
    color: #9ca3af;
  }
  
  /* Table styles */
  .tiptap-editor table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
    overflow: hidden;
  }
  
  .tiptap-editor th,
  .tiptap-editor td {
    border: 1px solid #d1d5db;
    padding: 0.5em 0.75em;
    text-align: left;
    vertical-align: top;
  }
  
  .tiptap-editor th {
    background-color: #f3f4f6;
    font-weight: 600;
  }
  
  .dark .tiptap-editor th {
    background-color: #374151;
  }
  
  .dark .tiptap-editor th,
  .dark .tiptap-editor td {
    border-color: #4b5563;
  }
  
  /* Image styles */
  .tiptap-editor img {
    max-width: 100%;
    height: auto;
    border-radius: 0.5rem;
    margin: 1em 0;
  }
  
  /* YouTube embed */
  .tiptap-editor iframe {
    max-width: 100%;
    border-radius: 0.5rem;
    margin: 1em 0;
  }
  
  /* Focus mode - highlight current node */
  .tiptap-editor .has-focus {
    border-radius: 4px;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);
  }
  
  /* Text alignment */
  .tiptap-editor .text-left { text-align: left; }
  .tiptap-editor .text-center { text-align: center; }
  .tiptap-editor .text-right { text-align: right; }
  .tiptap-editor .text-justify { text-align: justify; }
  
  /* Placeholder */
  .tiptap-editor p.is-editor-empty:first-child::before {
    color: #adb5bd;
    content: attr(data-placeholder);
    float: left;
    height: 0;
    pointer-events: none;
  }
`;

interface TiptapEditorProps {
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

// Toolbar Button Component
function ToolbarButton({
  onClick,
  isActive,
  disabled,
  title,
  children,
  className = "",
}: {
  onClick: () => void;
  isActive?: boolean;
  disabled?: boolean;
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`p-1.5 rounded text-sm font-medium transition-colors ${
        isActive
          ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
          : "text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""} ${className}`}
    >
      {children}
    </button>
  );
}

// Color Picker Dropdown
function ColorPicker({
  colors,
  onSelect,
  isHighlight,
  currentColor,
}: {
  colors: { name: string; color: string | null }[];
  onSelect: (color: string | null) => void;
  isHighlight?: boolean;
  currentColor?: string | null;
}) {
  const [open, setOpen] = useState(false);
  
  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="p-1.5 rounded text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 flex items-center gap-1"
        title={isHighlight ? "Highlight Color" : "Text Color"}
      >
        {isHighlight ? (
          <span 
            className="w-4 h-4 rounded border border-gray-400" 
            style={{ backgroundColor: currentColor || "#fef08a" }}
          />
        ) : (
          <span className="w-4 h-4 flex items-center justify-center font-bold" style={{ color: currentColor || "inherit" }}>A</span>
        )}
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute top-full left-0 mt-1 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-2 z-50 min-w-[120px]">
            {colors.map((c) => (
              <button
                key={c.name}
                onClick={() => {
                  onSelect(c.color);
                  setOpen(false);
                }}
                className="w-full flex items-center gap-2 px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-sm text-left"
              >
                {c.color ? (
                  <span
                    className="w-4 h-4 rounded border border-gray-300"
                    style={{ backgroundColor: c.color }}
                  />
                ) : (
                  <span className="w-4 h-4 rounded border border-gray-300 flex items-center justify-center text-xs">✕</span>
                )}
                <span className="text-gray-700 dark:text-gray-200">{c.name}</span>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// Link Edit Modal
function LinkModal({
  isOpen,
  onClose,
  onSubmit,
  initialUrl,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (url: string) => void;
  initialUrl?: string;
}) {
  const [url, setUrl] = useState(initialUrl || "");
  
  useEffect(() => {
    setUrl(initialUrl || "");
  }, [initialUrl, isOpen]);
  
  if (!isOpen) return null;
  
  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white dark:bg-gray-800 rounded-lg shadow-xl p-4 z-50 w-96">
        <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-white">Edit Link</h3>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://example.com"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white mb-3"
          autoFocus
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              onSubmit(url);
              onClose();
            }
          }}
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onSubmit(url);
              onClose();
            }}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Save
          </button>
          {initialUrl && (
            <button
              onClick={() => {
                onSubmit("");
                onClose();
              }}
              className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
            >
              Remove
            </button>
          )}
        </div>
      </div>
    </>
  );
}

// Image Insert Modal
function ImageModal({
  isOpen,
  onClose,
  onSubmit,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (url: string, alt?: string) => void;
}) {
  const [url, setUrl] = useState("");
  const [alt, setAlt] = useState("");
  
  if (!isOpen) return null;
  
  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white dark:bg-gray-800 rounded-lg shadow-xl p-4 z-50 w-96">
        <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-white">Insert Image</h3>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Image URL"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white mb-2"
          autoFocus
        />
        <input
          type="text"
          value={alt}
          onChange={(e) => setAlt(e.target.value)}
          placeholder="Alt text (optional)"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white mb-3"
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              if (url) {
                onSubmit(url, alt);
                setUrl("");
                setAlt("");
                onClose();
              }
            }}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Insert
          </button>
        </div>
      </div>
    </>
  );
}

// YouTube Insert Modal
function YoutubeModal({
  isOpen,
  onClose,
  onSubmit,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (url: string) => void;
}) {
  const [url, setUrl] = useState("");
  
  if (!isOpen) return null;
  
  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white dark:bg-gray-800 rounded-lg shadow-xl p-4 z-50 w-96">
        <h3 className="text-lg font-semibold mb-3 text-gray-900 dark:text-white">Embed YouTube Video</h3>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="YouTube URL"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white mb-3"
          autoFocus
        />
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              if (url) {
                onSubmit(url);
                setUrl("");
                onClose();
              }
            }}
            className="px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
          >
            Embed
          </button>
        </div>
      </div>
    </>
  );
}

// Toolbar Divider
function ToolbarDivider() {
  return <div className="w-px h-6 bg-gray-200 dark:bg-gray-600 mx-1" />;
}

export default function TiptapEditor({
  initialValue,
  onChange,
  onTogglePrompting,
  onToggleEditing,
  onCreateArtifact,
  onHighlight,
}: TiptapEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    visible: false,
    x: 0,
    y: 0,
    selectedText: "",
  });
  const [linkModalOpen, setLinkModalOpen] = useState(false);
  const [imageModalOpen, setImageModalOpen] = useState(false);
  const [youtubeModalOpen, setYoutubeModalOpen] = useState(false);
  const [currentLinkUrl, setCurrentLinkUrl] = useState<string | undefined>();
  
  // Convert markdown to HTML for initial content
  const initialHtml = React.useMemo(() => {
    // Pre-process ==highlight== syntax to <mark> tags
    let processed = initialValue.replace(/==([^=]+)==/g, "<mark>$1</mark>");
    // Pre-process ^superscript^
    processed = processed.replace(/\^([^^]+)\^/g, "<sup>$1</sup>");
    // Pre-process ~subscript~ (single tilde, not ~~strikethrough~~)
    processed = processed.replace(/(?<!\~)\~([^~]+)\~(?!\~)/g, "<sub>$1</sub>");
    return marked.parse(processed) as string;
  }, [initialValue]);

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: {
          levels: [1, 2, 3, 4, 5, 6],
        },
      }),
      Highlight.configure({
        multicolor: true,
      }),
      Typography,
      Placeholder.configure({
        placeholder: "Start writing your document...",
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
      TextStyle,
      Color,
      Underline,
      CharacterCount,
      TextAlign.configure({
        types: ["heading", "paragraph"],
      }),
      Link.configure({
        openOnClick: false,
        HTMLAttributes: {
          rel: "noopener noreferrer",
          target: "_blank",
        },
      }),
      Image.configure({
        HTMLAttributes: {
          class: "editor-image",
        },
      }),
      Youtube.configure({
        width: 640,
        height: 360,
      }),
      Superscript,
      Subscript,
      Focus.configure({
        className: "has-focus",
        mode: "deepest",
      }),
    ],
    content: initialHtml,
    editorProps: {
      attributes: {
        class: "tiptap-editor",
      },
    },
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      const markdown = turndownService.turndown(html);
      onChange(markdown);
    },
  });

  // Update content when initialValue changes externally
  const initialValueRef = useRef(initialValue);
  useEffect(() => {
    if (editor && initialValue !== initialValueRef.current) {
      initialValueRef.current = initialValue;
      let processed = initialValue.replace(/==([^=]+)==/g, "<mark>$1</mark>");
      processed = processed.replace(/\^([^^]+)\^/g, "<sup>$1</sup>");
      processed = processed.replace(/(?<!\~)\~([^~]+)\~(?!\~)/g, "<sub>$1</sub>");
      const html = marked.parse(processed) as string;
      editor.commands.setContent(html);
    }
  }, [initialValue, editor]);

  // Get selected text
  const getSelectedText = useCallback(() => {
    if (!editor) return "";
    const { from, to } = editor.state.selection;
    if (from === to) return "";
    return editor.state.doc.textBetween(from, to, " ");
  }, [editor]);

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
    setContextMenu((prev) => ({ ...prev, visible: false }));
  }, []);

  // Close menu on click outside
  useEffect(() => {
    const handleClick = () => closeMenu();
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, [closeMenu]);

  // Open link modal
  const openLinkModal = useCallback(() => {
    if (!editor) return;
    const previousUrl = editor.getAttributes("link").href;
    setCurrentLinkUrl(previousUrl);
    setLinkModalOpen(true);
  }, [editor]);

  // Set link
  const setLink = useCallback((url: string) => {
    if (!editor) return;
    if (url === "") {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
    } else {
      editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
    }
  }, [editor]);

  // Menu item component
  const MenuItem = ({
    label,
    onClick,
    disabled,
  }: {
    label: string;
    onClick: () => void;
    disabled?: boolean;
  }) => (
    <div
      onClick={(e) => {
        e.stopPropagation();
        if (!disabled) {
          onClick();
          closeMenu();
        }
      }}
      className={`px-3 py-1.5 text-sm cursor-pointer transition-colors ${
        disabled
          ? "text-gray-400 cursor-not-allowed"
          : "text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
      }`}
    >
      {label}
    </div>
  );

  const Divider = () => <div className="border-t border-gray-200 dark:border-gray-600 my-1" />;

  const hasSelection = contextMenu.selectedText.length > 0;

  if (!editor) {
    return <div className="p-4 text-gray-500">Loading editor...</div>;
  }

  const characterCount = editor.storage.characterCount;

  return (
    <div ref={containerRef} className="h-full flex flex-col" onContextMenu={handleContextMenu}>
      <style>{editorStyles}</style>
      
      {/* Toolbar */}
      <div className="flex items-center gap-0.5 px-2 py-1.5 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex-wrap">
        {/* Headings */}
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
          isActive={editor.isActive("heading", { level: 1 })}
          title="Heading 1"
        >
          H1
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          isActive={editor.isActive("heading", { level: 2 })}
          title="Heading 2"
        >
          H2
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          isActive={editor.isActive("heading", { level: 3 })}
          title="Heading 3"
        >
          H3
        </ToolbarButton>
        
        <ToolbarDivider />
        
        {/* Text formatting */}
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBold().run()}
          isActive={editor.isActive("bold")}
          title="Bold (Ctrl+B)"
        >
          <strong>B</strong>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleItalic().run()}
          isActive={editor.isActive("italic")}
          title="Italic (Ctrl+I)"
        >
          <em>I</em>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleUnderline().run()}
          isActive={editor.isActive("underline")}
          title="Underline (Ctrl+U)"
        >
          <u>U</u>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleStrike().run()}
          isActive={editor.isActive("strike")}
          title="Strikethrough"
        >
          <s>S</s>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleSuperscript().run()}
          isActive={editor.isActive("superscript")}
          title="Superscript"
        >
          X<sup>2</sup>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleSubscript().run()}
          isActive={editor.isActive("subscript")}
          title="Subscript"
        >
          X<sub>2</sub>
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleCode().run()}
          isActive={editor.isActive("code")}
          title="Inline Code"
        >
          {"</>"}
        </ToolbarButton>
        
        <ToolbarDivider />
        
        {/* Colors */}
        <ColorPicker
          colors={TEXT_COLORS}
          currentColor={editor.getAttributes("textStyle").color}
          onSelect={(color) => {
            if (color) {
              editor.chain().focus().setColor(color).run();
            } else {
              editor.chain().focus().unsetColor().run();
            }
          }}
        />
        <ColorPicker
          colors={HIGHLIGHT_COLORS}
          currentColor={editor.getAttributes("highlight").color}
          onSelect={(color) => {
            if (color) {
              editor.chain().focus().toggleHighlight({ color }).run();
            } else {
              editor.chain().focus().unsetHighlight().run();
            }
          }}
          isHighlight
        />
        
        <ToolbarDivider />
        
        {/* Text Align */}
        <ToolbarButton
          onClick={() => editor.chain().focus().setTextAlign("left").run()}
          isActive={editor.isActive({ textAlign: "left" })}
          title="Align Left"
        >
          ≡
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().setTextAlign("center").run()}
          isActive={editor.isActive({ textAlign: "center" })}
          title="Align Center"
        >
          ≡
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().setTextAlign("right").run()}
          isActive={editor.isActive({ textAlign: "right" })}
          title="Align Right"
        >
          ≡
        </ToolbarButton>
        
        <ToolbarDivider />
        
        {/* Lists */}
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          isActive={editor.isActive("bulletList")}
          title="Bullet List"
        >
          •
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          isActive={editor.isActive("orderedList")}
          title="Numbered List"
        >
          1.
        </ToolbarButton>
        
        <ToolbarDivider />
        
        {/* Links & Media */}
        <ToolbarButton
          onClick={openLinkModal}
          isActive={editor.isActive("link")}
          title="Insert Link"
        >
          🔗
        </ToolbarButton>
        <ToolbarButton
          onClick={() => setImageModalOpen(true)}
          title="Insert Image"
        >
          🖼️
        </ToolbarButton>
        <ToolbarButton
          onClick={() => setYoutubeModalOpen(true)}
          title="Embed YouTube"
        >
          ▶️
        </ToolbarButton>
        
        <ToolbarDivider />
        
        {/* Block elements */}
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBlockquote().run()}
          isActive={editor.isActive("blockquote")}
          title="Quote"
        >
          {'"'}
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleCodeBlock().run()}
          isActive={editor.isActive("codeBlock")}
          title="Code Block"
        >
          {"{ }"}
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().setHorizontalRule().run()}
          title="Horizontal Rule"
        >
          ―
        </ToolbarButton>
        
        <ToolbarDivider />
        
        {/* Undo/Redo */}
        <ToolbarButton
          onClick={() => editor.chain().focus().undo().run()}
          disabled={!editor.can().undo()}
          title="Undo (Ctrl+Z)"
        >
          ↩
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().redo().run()}
          disabled={!editor.can().redo()}
          title="Redo (Ctrl+Y)"
        >
          ↪
        </ToolbarButton>
      </div>
      
      {/* Editor Content */}
      <EditorContent editor={editor} className="flex-1 overflow-auto" />
      
      {/* Character Count Footer */}
      <div className="flex items-center justify-between px-3 py-1.5 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-4">
          <span>{characterCount?.characters() || 0} characters</span>
          <span>{characterCount?.words() || 0} words</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500" title="Focus mode active" />
          <span>Focus mode</span>
        </div>
      </div>
      
      {/* Modals */}
      <LinkModal
        isOpen={linkModalOpen}
        onClose={() => setLinkModalOpen(false)}
        onSubmit={setLink}
        initialUrl={currentLinkUrl}
      />
      <ImageModal
        isOpen={imageModalOpen}
        onClose={() => setImageModalOpen(false)}
        onSubmit={(url, alt) => {
          editor.chain().focus().setImage({ src: url, alt }).run();
        }}
      />
      <YoutubeModal
        isOpen={youtubeModalOpen}
        onClose={() => setYoutubeModalOpen(false)}
        onSubmit={(url) => {
          editor.commands.setYoutubeVideo({ src: url });
        }}
      />
      
      {/* Context Menu */}
      {contextMenu.visible && (
        <div
          className="fixed z-50 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 min-w-[180px]"
          style={{
            left: contextMenu.x,
            top: contextMenu.y,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <MenuItem
            label="✨ Toggle for prompting"
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
            onClick={() => {
              editor.chain().focus().toggleHighlight().run();
              onHighlight?.(contextMenu.selectedText);
            }}
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
